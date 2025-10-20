variable "environment" {
  description = "Environment name"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
}

variable "notification_email" {
  description = "Email for notifications"
  type        = string
}

variable "cost_threshold" {
  description = "Cost threshold for anomaly detection"
  type        = number
}

variable "lambda_function_arns" {
  description = "Map of Lambda function ARNs"
  type        = map(string)
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
}
