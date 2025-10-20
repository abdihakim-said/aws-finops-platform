# AWS FinOps Platform - Enterprise Infrastructure

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
  region = var.aws_region
  
  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      Owner       = "platform-team"
      CostCenter  = "engineering"
      Purpose     = "cost-optimization"
      ManagedBy   = "terraform"
    }
  }
}

# Data sources for account information
data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# IAM Module - Enterprise security with least privilege
module "iam" {
  source = "./modules/iam"
  
  environment    = var.environment
  project_name   = var.project_name
  common_tags    = local.common_tags
}

# Lambda Functions Module - All cost optimization functions
module "lambda_functions" {
  source = "./modules/lambda"
  
  environment               = var.environment
  project_name             = var.project_name
  lambda_execution_role_arn = module.iam.lambda_execution_role_arn
  
  # Enterprise Lambda configuration
  lambda_functions = local.lambda_functions
  lambda_schedules = local.lambda_schedules
  
  # Monitoring and alerting
  sns_topic_arn = module.monitoring.sns_topic_arn
  
  common_tags = local.common_tags
  
  depends_on = [module.iam]
}

# Monitoring Module - CloudWatch dashboards, alarms, SNS
module "monitoring" {
  source = "./modules/monitoring"
  
  environment         = var.environment
  project_name       = var.project_name
  notification_email = var.notification_email
  cost_threshold     = var.cost_threshold
  
  # Lambda function ARNs for monitoring
  lambda_function_arns = module.lambda_functions.lambda_function_arns
  
  common_tags = local.common_tags
}

# Storage Module - S3 buckets for reports, DynamoDB for state
module "storage" {
  source = "./modules/storage"
  
  environment  = var.environment
  project_name = var.project_name
  common_tags  = local.common_tags
}

# Local values - Enterprise configuration
locals {
  common_tags = {
    Project     = var.project_name
    Environment = var.environment
    Owner       = "platform-team"
    CostCenter  = "engineering"
    Purpose     = "cost-optimization"
    ManagedBy   = "terraform"
    Account     = data.aws_caller_identity.current.account_id
    Region      = data.aws_region.current.name
  }
  
  # Enterprise Lambda function definitions
  lambda_functions = {
    # Tier 1: Critical Cost Optimization (Daily)
    cost-optimizer = {
      source_file = "cost_optimizer.py"
      handler     = "cost_optimizer.lambda_handler"
      timeout     = 300
      memory_size = 512
      tier        = "critical"
      env_vars = {
        FUNCTION_TYPE = "cost_optimization"
        TIER         = "critical"
      }
    }
    
    s3-lifecycle-optimizer = {
      source_file = "s3_lifecycle_optimizer.py"
      handler     = "s3_lifecycle_optimizer.lambda_handler"
      timeout     = 300
      memory_size = 256
      tier        = "critical"
      env_vars = {
        FUNCTION_TYPE = "storage_optimization"
        TIER         = "critical"
      }
    }
    
    unused-resources-cleanup = {
      source_file = "unused_resources_cleanup.py"
      handler     = "unused_resources_cleanup.lambda_handler"
      timeout     = 600
      memory_size = 512
      tier        = "critical"
      env_vars = {
        FUNCTION_TYPE = "resource_management"
        TIER         = "critical"
      }
    }
    
    # Tier 2: Strategic Optimization (Weekly)
    ec2-rightsizing = {
      source_file = "ec2_rightsizing.py"
      handler     = "ec2_rightsizing.lambda_handler"
      timeout     = 900
      memory_size = 1024
      tier        = "strategic"
      env_vars = {
        FUNCTION_TYPE = "cost_optimization"
        CPU_THRESHOLD = "20"
        TIER         = "strategic"
      }
    }
    
    rds-optimizer = {
      source_file = "rds_optimizer.py"
      handler     = "rds_optimizer.lambda_handler"
      timeout     = 600
      memory_size = 512
      tier        = "strategic"
      env_vars = {
        FUNCTION_TYPE = "cost_optimization"
        IDLE_THRESHOLD_DAYS = "7"
        TIER               = "strategic"
      }
    }
    
    ri-optimizer = {
      source_file = "ri_optimizer.py"
      handler     = "ri_optimizer.lambda_handler"
      timeout     = 600
      memory_size = 1024
      tier        = "strategic"
      env_vars = {
        FUNCTION_TYPE = "resource_management"
        TIER         = "strategic"
      }
    }
    
    spot-optimizer = {
      source_file = "spot_optimizer.py"
      handler     = "spot_optimizer.lambda_handler"
      timeout     = 300
      memory_size = 512
      tier        = "strategic"
      env_vars = {
        FUNCTION_TYPE = "resource_management"
        TIER         = "strategic"
      }
    }
    
    # Tier 3: Advanced Analytics (Real-time/Monthly)
    ml-cost-anomaly-detector = {
      source_file = "ml_cost_anomaly_detector.py"
      handler     = "ml_cost_anomaly_detector.lambda_handler"
      timeout     = 900
      memory_size = 2048
      tier        = "analytics"
      env_vars = {
        FUNCTION_TYPE = "analytics"
        TIER         = "analytics"
      }
    }
    
    k8s-resource-optimizer = {
      source_file = "k8s_resource_optimizer.py"
      handler     = "k8s_resource_optimizer.lambda_handler"
      timeout     = 900
      memory_size = 1024
      tier        = "analytics"
      env_vars = {
        FUNCTION_TYPE = "analytics"
        TIER         = "analytics"
      }
    }
    
    data-transfer-optimizer = {
      source_file = "data_transfer_optimizer.py"
      handler     = "data_transfer_optimizer.lambda_handler"
      timeout     = 600
      memory_size = 512
      tier        = "analytics"
      env_vars = {
        FUNCTION_TYPE = "analytics"
        TIER         = "analytics"
      }
    }
    
    # Tier 4: Enterprise Governance (Monthly)
    multi-account-governance = {
      source_file = "multi_account_governance.py"
      handler     = "multi_account_governance.lambda_handler"
      timeout     = 1800
      memory_size = 2048
      tier        = "governance"
      env_vars = {
        FUNCTION_TYPE = "governance"
        TIER         = "governance"
      }
    }
  }
  
  # Enterprise scheduling strategy
  lambda_schedules = {
    # Tier 1: Critical daily optimizations (off-peak hours)
    cost-optimizer           = "cron(0 2 * * ? *)"    # 2 AM UTC daily
    s3-lifecycle-optimizer   = "cron(0 3 * * ? *)"    # 3 AM UTC daily  
    unused-resources-cleanup = "cron(0 4 * * ? *)"    # 4 AM UTC daily
    
    # Tier 2: Strategic weekly analysis (Sunday mornings)
    ec2-rightsizing = "cron(0 6 ? * SUN *)"   # 6 AM UTC Sundays
    rds-optimizer   = "cron(0 7 ? * SUN *)"   # 7 AM UTC Sundays
    ri-optimizer    = "cron(0 8 ? * SUN *)"   # 8 AM UTC Sundays
    spot-optimizer  = "cron(0 9 ? * SUN *)"   # 9 AM UTC Sundays
    
    # Tier 3: Advanced analytics
    ml-cost-anomaly-detector = "rate(1 hour)"         # Continuous monitoring
    k8s-resource-optimizer   = "cron(0 10 ? * SUN *)" # 10 AM UTC Sundays
    data-transfer-optimizer  = "cron(0 11 ? * SUN *)" # 11 AM UTC Sundays
    
    # Tier 4: Enterprise governance (monthly)
    multi-account-governance = "cron(0 12 1 * ? *)"   # 12 PM UTC 1st of month
  }
}
