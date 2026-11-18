variable "project" {
  type    = string
  default = "acf"
}

variable "environment" {
  type    = string
  default = "prod"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod."
  }
}

variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}

variable "az_count" {
  type    = number
  default = 2
}

variable "backend_image" {
  description = "Backend image URI (defaults to :latest in the created ECR repo)."
  type        = string
  default     = ""
}

variable "frontend_image" {
  description = "Frontend image URI (defaults to :latest in the created ECR repo)."
  type        = string
  default     = ""
}

variable "backend_cpu" {
  type    = number
  default = 512
}

variable "backend_memory" {
  type    = number
  default = 1024
}

variable "worker_cpu" {
  type    = number
  default = 1024
}

variable "worker_memory" {
  type    = number
  default = 2048
}

variable "frontend_cpu" {
  type    = number
  default = 256
}

variable "frontend_memory" {
  type    = number
  default = 512
}

variable "backend_desired_count" {
  type    = number
  default = 2
}

variable "worker_desired_count" {
  type    = number
  default = 2
}

variable "frontend_desired_count" {
  type    = number
  default = 2
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.medium"
}

variable "db_allocated_storage" {
  type    = number
  default = 50
}

variable "db_multi_az" {
  type    = bool
  default = true
}

variable "redis_node_type" {
  type    = string
  default = "cache.t4g.small"
}

variable "log_retention_days" {
  type    = number
  default = 30
}

variable "certificate_arn" {
  description = "ACM certificate for HTTPS on the ALB. Leave empty for HTTP only (non-production)."
  type        = string
  default     = ""
}

variable "public_url" {
  description = "Public base URL users reach the app at (used for CORS and the frontend API URL)."
  type        = string
  default     = ""
}

variable "alarm_email" {
  type    = string
  default = ""
}

variable "publishing_dry_run" {
  type    = bool
  default = false
}
