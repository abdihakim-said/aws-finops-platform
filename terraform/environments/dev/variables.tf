variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "notification_email" {
  description = "Email for cost optimization alerts"
  type        = string
}

variable "cost_threshold" {
  description = "Monthly cost threshold for alerts (USD)"
  type        = number
  default     = 1000  # Development threshold
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "development"
    Project     = "finops-platform"
    ManagedBy   = "terraform"
    Owner       = "dev-team"
  }
}
