variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  type        = string
}

variable "runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.9"
}

variable "lambda_functions" {
  description = "Map of Lambda function configurations"
  type = map(object({
    source_file = string
    handler     = string
    timeout     = number
    memory_size = number
    tier        = string
    env_vars    = map(string)
  }))
}

variable "lambda_schedules" {
  description = "Map of Lambda function schedules"
  type        = map(string)
}

variable "common_env_vars" {
  description = "Common environment variables for all functions"
  type        = map(string)
  default     = {}
}

variable "sns_topic_arn" {
  description = "SNS topic ARN for notifications"
  type        = string
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
}
