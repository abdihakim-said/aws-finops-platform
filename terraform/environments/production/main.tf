# Production Environment - AWS FinOps Platform

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.20"  # Updated version for Cost Explorer support
    }
  }
}

provider "aws" {
  region = "us-east-1"
  
  default_tags {
    tags = {
      Environment = "production"
      Project     = "aws-finops-platform"
      Owner       = "platform-team"
      CostCenter  = "engineering"
      Compliance  = "required"
      ManagedBy   = "terraform"
    }
  }
}

# Use the parent modules
module "iam" {
  source = "../../modules/iam"
  
  environment  = "production"
  project_name = "aws-finops-platform"
  common_tags = {
    Environment = "production"
    Project     = "aws-finops-platform"
    CostCenter  = "engineering"
    Compliance  = "required"
  }
}

module "storage" {
  source = "../../modules/storage"
  
  environment  = "production"
  project_name = "aws-finops-platform"
  common_tags = {
    Environment = "production"
    Project     = "aws-finops-platform"
    Compliance  = "required"
  }
}

module "monitoring" {
  source = "../../modules/monitoring"
  
  environment         = "production"
  project_name       = "aws-finops-platform"
  notification_email = "finops-alerts@company.com"
  cost_threshold     = 10000
  lambda_function_arns = module.lambda_functions.lambda_function_arns
  common_tags = {
    Environment = "production"
    Project     = "aws-finops-platform"
    Compliance  = "required"
  }
}

module "lambda_functions" {
  source = "../../modules/lambda"
  
  environment               = "production"
  project_name             = "aws-finops-platform"
  lambda_execution_role_arn = module.iam.lambda_execution_role_arn
  
  # Production: ALL 11 Lambda functions
  lambda_functions = {
    cost-optimizer = {
      source_file = "cost_optimizer.py"
      handler     = "cost_optimizer.lambda_handler"
      timeout     = 300
      memory_size = 512
      tier        = "critical"
      env_vars = {
        FUNCTION_TYPE = "cost_optimization"
        ENVIRONMENT   = "production"
      }
    }
    
    ec2-rightsizing = {
      source_file = "ec2_rightsizing.py"
      handler     = "ec2_rightsizing.lambda_handler"
      timeout     = 900
      memory_size = 1024
      tier        = "strategic"
      env_vars = {
        FUNCTION_TYPE = "cost_optimization"
        CPU_THRESHOLD = "20"
        ENVIRONMENT   = "production"
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
        ENVIRONMENT   = "production"
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
        ENVIRONMENT   = "production"
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
        ENVIRONMENT   = "production"
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
        ENVIRONMENT   = "production"
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
        ENVIRONMENT   = "production"
      }
    }
    
    ml-cost-anomaly-detector = {
      source_file = "ml_cost_anomaly_detector.py"
      handler     = "ml_cost_anomaly_detector.lambda_handler"
      timeout     = 900
      memory_size = 2048
      tier        = "analytics"
      env_vars = {
        FUNCTION_TYPE = "analytics"
        ENVIRONMENT   = "production"
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
        ENVIRONMENT   = "production"
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
        ENVIRONMENT   = "production"
      }
    }
    
    multi-account-governance = {
      source_file = "multi_account_governance.py"
      handler     = "multi_account_governance.lambda_handler"
      timeout     = 900
      memory_size = 2048
      tier        = "governance"
      env_vars = {
        FUNCTION_TYPE = "governance"
        ENVIRONMENT   = "production"
      }
    }
  }
  
  # Production schedules (full enterprise automation)
  lambda_schedules = {
    # Critical daily optimizations (2-4 AM UTC)
    cost-optimizer           = "cron(0 2 * * ? *)"
    s3-lifecycle-optimizer   = "cron(0 3 * * ? *)"
    unused-resources-cleanup = "cron(0 4 * * ? *)"
    
    # Strategic weekly analysis (Sundays 6-11 AM UTC)
    ec2-rightsizing         = "cron(0 6 ? * SUN *)"
    rds-optimizer          = "cron(0 7 ? * SUN *)"
    ri-optimizer           = "cron(0 8 ? * SUN *)"
    spot-optimizer         = "cron(0 9 ? * SUN *)"
    k8s-resource-optimizer = "cron(0 10 ? * SUN *)"
    data-transfer-optimizer = "cron(0 11 ? * SUN *)"
    
    # Real-time analytics
    ml-cost-anomaly-detector = "rate(1 hour)"
    
    # Monthly governance (1st of month)
    multi-account-governance = "cron(0 12 1 * ? *)"
  }
  
  common_env_vars = {
    ENVIRONMENT = "production"
    REGION      = "us-east-1"
    PROJECT     = "aws-finops-platform"
    LOG_LEVEL   = "WARN"
  }
  
  sns_topic_arn = module.monitoring.sns_topic_arn
  common_tags = {
    Environment = "production"
    Project     = "aws-finops-platform"
    Compliance  = "required"
  }
  
  depends_on = [module.iam, module.storage]
}

# Production outputs
output "lambda_function_names" {
  description = "Production Lambda function names"
  value       = module.lambda_functions.lambda_function_names
}

output "dashboard_url" {
  description = "Production CloudWatch dashboard"
  value       = module.monitoring.dashboard_url
}

output "estimated_monthly_savings" {
  description = "Estimated monthly cost savings"
  value = {
    critical_functions  = "£5,000-12,000"
    strategic_functions = "£8,000-25,000"
    analytics_functions = "£2,000-8,000"
    governance_functions = "£1,000-5,000"
    total_potential     = "£16,000-50,000"
  }
}
