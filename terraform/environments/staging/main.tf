# Staging Environment - AWS FinOps Platform

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    # Configure during terraform init
    # bucket = "finops-platform-terraform-state-staging"
    # key    = "environments/staging/terraform.tfstate"
    # region = "us-east-1"
  }
}

provider "aws" {
  region = "us-east-1"
  
  default_tags {
    tags = {
      Environment = "staging"
      Project     = "aws-finops-platform"
      Owner       = "platform-team"
      ManagedBy   = "terraform"
    }
  }
}

# Use the parent modules
module "iam" {
  source = "../../modules/iam"
  
  environment  = "staging"
  project_name = "aws-finops-platform"
  common_tags = {
    Environment = "staging"
    Project     = "aws-finops-platform"
    CostCenter  = "engineering"
  }
}

module "storage" {
  source = "../../modules/storage"
  
  environment  = "staging"
  project_name = "aws-finops-platform"
  common_tags = {
    Environment = "staging"
    Project     = "aws-finops-platform"
  }
}

module "monitoring" {
  source = "../../modules/monitoring"
  
  environment         = "staging"
  project_name       = "aws-finops-platform"
  notification_email = "staging-alerts@company.com"
  cost_threshold     = 2000
  lambda_function_arns = module.lambda_functions.lambda_function_arns
  common_tags = {
    Environment = "staging"
    Project     = "aws-finops-platform"
  }
}

module "lambda_functions" {
  source = "../../modules/lambda"
  
  environment               = "staging"
  project_name             = "aws-finops-platform"
  lambda_execution_role_arn = module.iam.lambda_execution_role_arn
  
  # Staging: Most functions for pre-prod testing
  lambda_functions = {
    cost-optimizer = {
      source_file = "cost_optimizer.py"
      handler     = "cost_optimizer.lambda_handler"
      timeout     = 300
      memory_size = 512
      tier        = "critical"
      env_vars = {
        FUNCTION_TYPE = "cost_optimization"
        ENVIRONMENT   = "staging"
      }
    }
    
    ec2-rightsizing = {
      source_file = "ec2_rightsizing.py"
      handler     = "ec2_rightsizing.lambda_handler"
      timeout     = 600
      memory_size = 1024
      tier        = "strategic"
      env_vars = {
        FUNCTION_TYPE = "cost_optimization"
        CPU_THRESHOLD = "20"
        ENVIRONMENT   = "staging"
      }
    }
    
    rds-optimizer = {
      source_file = "rds_optimizer.py"
      handler     = "rds_optimizer.lambda_handler"
      timeout     = 300
      memory_size = 512
      tier        = "strategic"
      env_vars = {
        FUNCTION_TYPE = "cost_optimization"
        ENVIRONMENT   = "staging"
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
        ENVIRONMENT   = "staging"
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
        ENVIRONMENT   = "staging"
      }
    }
    
    ri-optimizer = {
      source_file = "ri_optimizer.py"
      handler     = "ri_optimizer.lambda_handler"
      timeout     = 300
      memory_size = 512
      tier        = "strategic"
      env_vars = {
        FUNCTION_TYPE = "resource_management"
        ENVIRONMENT   = "staging"
      }
    }
    
    ml-cost-anomaly-detector = {
      source_file = "ml_cost_anomaly_detector.py"
      handler     = "ml_cost_anomaly_detector.lambda_handler"
      timeout     = 900
      memory_size = 1024
      tier        = "analytics"
      env_vars = {
        FUNCTION_TYPE = "analytics"
        ENVIRONMENT   = "staging"
      }
    }
  }
  
  # Staging schedules (production-like but less frequent)
  lambda_schedules = {
    cost-optimizer           = "cron(0 3 * * ? *)"    # 3 AM daily
    s3-lifecycle-optimizer   = "cron(0 4 * * ? *)"    # 4 AM daily
    unused-resources-cleanup = "cron(0 5 * * ? *)"    # 5 AM daily
    ec2-rightsizing         = "cron(0 8 ? * SUN *)"   # 8 AM Sundays
    rds-optimizer          = "cron(0 9 ? * SUN *)"    # 9 AM Sundays
    ri-optimizer           = "cron(0 10 ? * SUN *)"   # 10 AM Sundays
    ml-cost-anomaly-detector = "rate(2 hours)"        # Every 2 hours
  }
  
  common_env_vars = {
    ENVIRONMENT = "staging"
    REGION      = "us-east-1"
    PROJECT     = "aws-finops-platform"
    LOG_LEVEL   = "INFO"
  }
  
  sns_topic_arn = module.monitoring.sns_topic_arn
  common_tags = {
    Environment = "staging"
    Project     = "aws-finops-platform"
  }
  
  depends_on = [module.iam, module.storage]
}

# Outputs
output "lambda_function_names" {
  value = module.lambda_functions.lambda_function_names
}

output "dashboard_url" {
  value = module.monitoring.dashboard_url
}
