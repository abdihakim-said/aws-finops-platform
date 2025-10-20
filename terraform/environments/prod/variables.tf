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
  default     = 50000 # Production threshold
}

variable "trusted_account_arns" {
  description = "List of trusted AWS account ARNs for cross-account access"
  type        = list(string)
  default     = []
}

variable "common_tags" {
  description = "Common tags for all resources"
  type        = map(string)
  default = {
    Environment = "production"
    Project     = "finops-platform"
    ManagedBy   = "terraform"
    Owner       = "sre-team"
    CostCenter  = "engineering"
  }
}
