# Production Environment - Parent Terraform configuration

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket = "finops-platform-terraform-state-prod"
    key    = "prod/terraform.tfstate"
    region = "us-east-1"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = "production"
      Project     = "finops-platform"
      ManagedBy   = "terraform"
      Owner       = "sre-team"
    }
  }
}

# Local values for production
locals {
  environment = "prod"

  lambda_functions = {
    cost-optimizer = {
      filename    = "cost_optimizer.zip"
      handler     = "cost_optimizer.lambda_handler"
      timeout     = 300
      memory_size = 512
      env_vars = {
        ENVIRONMENT = local.environment
        LOG_LEVEL   = "INFO"
      }
    }
    ec2-rightsizing = {
      filename    = "ec2_rightsizing.zip"
      handler     = "ec2_rightsizing.lambda_handler"
      timeout     = 600
      memory_size = 1024
      env_vars = {
        ENVIRONMENT = local.environment
        LOG_LEVEL   = "INFO"
      }
    }
    s3-lifecycle-optimizer = {
      filename    = "s3_lifecycle_optimizer.zip"
      handler     = "s3_lifecycle_optimizer.lambda_handler"
      timeout     = 900
      memory_size = 512
      env_vars = {
        ENVIRONMENT = local.environment
        LOG_LEVEL   = "INFO"
      }
    }
    eks-cost-optimizer = {
      filename    = "eks_cost_optimizer.zip"
      handler     = "eks_cost_optimizer.lambda_handler"
      timeout     = 600
      memory_size = 1024
      env_vars = {
        ENVIRONMENT = local.environment
        LOG_LEVEL   = "INFO"
      }
    }
  }

  lambda_schedules = {
    cost-optimizer         = "cron(0 2 * * ? *)" # Daily at 2 AM
    ec2-rightsizing        = "cron(0 3 * * ? *)" # Daily at 3 AM
    s3-lifecycle-optimizer = "cron(0 4 0 * ? *)" # Weekly
    eks-cost-optimizer     = "cron(0 5 * * ? *)" # Daily at 5 AM
  }
}

# IAM Module
module "iam" {
  source = "../../modules/iam"

  environment          = local.environment
  enable_cross_account = true
  trusted_account_arns = var.trusted_account_arns
  common_tags          = var.common_tags
}

# Lambda Module
module "lambda" {
  source = "../../modules/lambda"

  environment               = local.environment
  lambda_execution_role_arn = module.iam.lambda_execution_role_arn
  lambda_functions          = local.lambda_functions
  lambda_schedules          = local.lambda_schedules
  common_tags               = var.common_tags

  common_env_vars = {
    ENVIRONMENT = local.environment
    REGION      = var.aws_region
  }
}

# Monitoring Module
module "monitoring" {
  source = "../../modules/monitoring"

  environment           = local.environment
  aws_region            = var.aws_region
  notification_email    = var.notification_email
  cost_threshold        = var.cost_threshold
  lambda_function_names = keys(local.lambda_functions)
  common_tags           = var.common_tags
}
