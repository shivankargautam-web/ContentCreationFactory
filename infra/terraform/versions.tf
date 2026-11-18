terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.70"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
  # Configure remote state per environment, e.g.:
  # backend "s3" { bucket = "acf-tfstate" key = "prod/terraform.tfstate" region = "us-east-1" dynamodb_table = "acf-tflock" encrypt = true }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = local.tags
  }
}
