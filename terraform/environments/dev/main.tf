# Development Environment - AWS FinOps Platform

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
  
  default_tags {
    tags = {
      Environment = "dev"
      Project     = "aws-finops-platform"
      Owner       = "dev-team"
      ManagedBy   = "terraform"
    }
  }
}

# Use the parent modules
module "iam" {
  source = "../../modules/iam"
  
  environment  = "dev"
  project_name = "aws-finops-platform"
  common_tags = {
    Environment = "dev"
    Project     = "aws-finops-platform"
  }
}

module "storage" {
  source = "../../modules/storage"
  
  environment  = "dev"
  project_name = "aws-finops-platform"
  common_tags = {
    Environment = "dev"
    Project     = "aws-finops-platform"
  }
}

module "monitoring" {
  source = "../../modules/monitoring"
  
  environment         = "dev"
  project_name       = "aws-finops-platform"
  notification_email = "dev-team@company.com"
  cost_threshold     = 500
  lambda_function_arns = module.lambda_functions.lambda_function_arns
  common_tags = {
    Environment = "dev"
    Project     = "aws-finops-platform"
  }
}

module "lambda_functions" {
  source = "../../modules/lambda"
  
  environment               = "dev"
  project_name             = "aws-finops-platform"
  lambda_execution_role_arn = module.iam.lambda_execution_role_arn
  
  # Dev Lambda functions (subset for testing)
  lambda_functions = {
    cost-optimizer = {
      source_file = "cost_optimizer.py"
      handler     = "cost_optimizer.lambda_handler"
      timeout     = 300
      memory_size = 512
      tier        = "critical"
      env_vars = {
        FUNCTION_TYPE = "cost_optimization"
        ENVIRONMENT   = "dev"
      }
    }
    
    ec2-rightsizing = {
      source_file = "ec2_rightsizing.py"
      handler     = "ec2_rightsizing.lambda_handler"
      timeout     = 300
      memory_size = 512
      tier        = "strategic"
      env_vars = {
        FUNCTION_TYPE = "cost_optimization"
        CPU_THRESHOLD = "20"
        ENVIRONMENT   = "dev"
      }
    }
    
    unused-resources-cleanup = {
      source_file = "unused_resources_cleanup.py"
      handler     = "unused_resources_cleanup.lambda_handler"
      timeout     = 300
      memory_size = 256
      tier        = "critical"
      env_vars = {
        FUNCTION_TYPE = "resource_management"
        ENVIRONMENT   = "dev"
      }
    }
  }
  
  # Dev schedules (less frequent for testing)
  lambda_schedules = {
    cost-optimizer           = "cron(0 10 * * ? *)"    # 10 AM daily for testing
    ec2-rightsizing         = "cron(0 14 ? * MON *)"   # 2 PM Mondays
    unused-resources-cleanup = "cron(0 16 ? * FRI *)"  # 4 PM Fridays
  }
  
  common_env_vars = {
    ENVIRONMENT = "dev"
    REGION      = "us-east-1"
    PROJECT     = "aws-finops-platform"
    LOG_LEVEL   = "DEBUG"
  }
  
  sns_topic_arn = module.monitoring.sns_topic_arn
  common_tags = {
    Environment = "dev"
    Project     = "aws-finops-platform"
  }
  
  depends_on = [module.iam, module.storage]
}

# Outputs for dev environment
output "lambda_function_names" {
  description = "Names of deployed Lambda functions"
  value       = module.lambda_functions.lambda_function_names
}

output "s3_bucket_name" {
  description = "S3 bucket for reports"
  value       = module.storage.reports_bucket_name
}

output "dashboard_url" {
  description = "CloudWatch dashboard URL"
  value       = module.monitoring.dashboard_url
}
