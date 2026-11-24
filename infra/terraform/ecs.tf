resource "aws_ecs_cluster" "this" {
  name = local.name
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name       = aws_ecs_cluster.this.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
  default_capacity_provider_strategy {
    capacity_provider = "FARGATE"
    weight            = 1
  }
}

locals {
  redis_url = "redis://${aws_elasticache_replication_group.redis.primary_endpoint_address}:6379/0"

  backend_environment = [
    { name = "ENVIRONMENT", value = var.environment == "prod" ? "production" : "staging" },
    { name = "REDIS_URL", value = local.redis_url },
    { name = "CORS_ORIGINS", value = local.public_url },
    { name = "PUBLIC_APP_URL", value = local.public_url },
    { name = "STORAGE_BACKEND", value = "s3" },
    { name = "S3_BUCKET", value = aws_s3_bucket.media.bucket },
    { name = "S3_REGION", value = var.aws_region },
    { name = "PUBLISHING_DRY_RUN", value = tostring(var.publishing_dry_run) },
    { name = "LOG_JSON", value = "true" },
    { name = "OTEL_ENABLED", value = "true" },
    { name = "OTEL_SERVICE_NAME", value = "acf-backend" },
    { name = "OTEL_EXPORTER_OTLP_ENDPOINT", value = "http://localhost:4317" },
  ]

  backend_secrets = [
    for key in ["DATABASE_URL", "JWT_SECRET_KEY", "TOKEN_ENCRYPTION_KEY", "OPENAI_API_KEY", "ELEVENLABS_API_KEY", "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "META_APP_ID", "META_APP_SECRET"] :
    { name = key, valueFrom = "${aws_secretsmanager_secret.app.arn}:${key}::" }
  ]

  # AWS Distro for OpenTelemetry sidecar: receives OTLP on :4317 and exports traces to X-Ray / metrics to CloudWatch.
  otel_sidecar = {
    name      = "otel-collector"
    image     = "public.ecr.aws/aws-observability/aws-otel-collector:v0.41.1"
    essential = false
    command   = ["--config=/etc/ecs/ecs-default-config.yaml"]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.this["otel"].name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "otel"
      }
    }
  }

  backend_services = {
    api = {
      cpu     = var.backend_cpu
      memory  = var.backend_memory
      count   = var.backend_desired_count
      command = ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 --proxy-headers"]
      port    = 8000
    }
    worker = {
      cpu     = var.worker_cpu
      memory  = var.worker_memory
      count   = var.worker_desired_count
      command = ["celery", "-A", "app.scheduler.celery_app:celery_app", "worker", "--loglevel=INFO", "-Q", "default,generation,publishing,analytics", "--concurrency=2"]
      port    = null
    }
    beat = {
      cpu     = 256
      memory  = 512
      count   = 1 # exactly one scheduler
      command = ["celery", "-A", "app.scheduler.celery_app:celery_app", "beat", "--loglevel=INFO", "--schedule=/tmp/celerybeat-schedule"]
      port    = null
    }
  }
}

locals {
  backend_container = {
    for key, svc in local.backend_services : key => {
      name        = key
      image       = local.backend_image
      essential   = true
      command     = svc.command
      environment = local.backend_environment
      secrets     = local.backend_secrets
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.this[key].name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = key
        }
      }
    }
  }
  web_container_extras = {
    portMappings = [{ containerPort = 8000, protocol = "tcp" }]
    healthCheck = {
      command     = ["CMD-SHELL", "curl -fsS http://localhost:8000/health/live || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }
}

resource "aws_ecs_task_definition" "backend" {
  for_each                 = local.backend_services
  family                   = "${local.name}-${each.key}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = each.value.cpu
  memory                   = each.value.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }
  ephemeral_storage {
    size_in_gib = each.key == "worker" ? 50 : 21 # ffmpeg scratch space
  }
  container_definitions = (
    each.value.port == null
    ? jsonencode([local.backend_container[each.key], local.otel_sidecar])
    : jsonencode([merge(local.backend_container[each.key], local.web_container_extras), local.otel_sidecar])
  )
}

resource "aws_ecs_task_definition" "frontend" {
  family                   = "${local.name}-frontend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.frontend_cpu
  memory                   = var.frontend_memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name         = "frontend"
    image        = local.frontend_image
    essential    = true
    portMappings = [{ containerPort = 3000, protocol = "tcp" }]
    environment  = [{ name = "NODE_ENV", value = "production" }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.this["frontend"].name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "frontend"
      }
    }
  }])
}

resource "aws_ecs_service" "backend" {
  for_each               = local.backend_services
  name                   = each.key
  cluster                = aws_ecs_cluster.this.id
  task_definition        = aws_ecs_task_definition.backend[each.key].arn
  desired_count          = each.value.count
  launch_type            = "FARGATE"
  enable_execute_command = true
  propagate_tags         = "SERVICE"

  deployment_minimum_healthy_percent = each.key == "beat" ? 0 : 100
  deployment_maximum_percent         = each.key == "beat" ? 100 : 200
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }

  dynamic "load_balancer" {
    for_each = each.value.port == null ? [] : [each.value.port]
    content {
      target_group_arn = aws_lb_target_group.backend.arn
      container_name   = each.key
      container_port   = load_balancer.value
    }
  }

  lifecycle {
    ignore_changes = [desired_count]
  }
  depends_on = [aws_lb_listener_rule.api]
}

resource "aws_ecs_service" "frontend" {
  name            = "frontend"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = var.frontend_desired_count
  launch_type     = "FARGATE"
  propagate_tags  = "SERVICE"
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }
  lifecycle {
    ignore_changes = [desired_count]
  }
}

# ---------------------------------------------------------------- autoscaling
locals {
  scalable = {
    api      = { service = aws_ecs_service.backend["api"].name, min = var.backend_desired_count, max = 10, target = 60 }
    worker   = { service = aws_ecs_service.backend["worker"].name, min = var.worker_desired_count, max = 20, target = 70 }
    frontend = { service = aws_ecs_service.frontend.name, min = var.frontend_desired_count, max = 6, target = 60 }
  }
}

resource "aws_appautoscaling_target" "this" {
  for_each           = local.scalable
  service_namespace  = "ecs"
  resource_id        = "service/${aws_ecs_cluster.this.name}/${each.value.service}"
  scalable_dimension = "ecs:service:DesiredCount"
  min_capacity       = each.value.min
  max_capacity       = each.value.max
}

resource "aws_appautoscaling_policy" "cpu" {
  for_each           = local.scalable
  name               = "${local.name}-${each.key}-cpu"
  policy_type        = "TargetTrackingScaling"
  service_namespace  = aws_appautoscaling_target.this[each.key].service_namespace
  resource_id        = aws_appautoscaling_target.this[each.key].resource_id
  scalable_dimension = aws_appautoscaling_target.this[each.key].scalable_dimension
  target_tracking_scaling_policy_configuration {
    target_value       = each.value.target
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
  }
}
