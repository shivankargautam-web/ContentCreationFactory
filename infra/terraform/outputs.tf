output "app_url" {
  value = local.public_url
}

output "alb_dns_name" {
  value = aws_lb.this.dns_name
}

output "ecr_repositories" {
  value = { for k, r in aws_ecr_repository.this : k => r.repository_url }
}

output "ecs_cluster" {
  value = aws_ecs_cluster.this.name
}

output "media_bucket" {
  value = aws_s3_bucket.media.bucket
}

output "rds_endpoint" {
  value = aws_db_instance.this.address
}

output "app_secret_arn" {
  value = aws_secretsmanager_secret.app.arn
}

output "cloudwatch_dashboard" {
  value = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.this.dashboard_name}"
}
