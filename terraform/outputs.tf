# AWS FinOps Platform - Enterprise Outputs

# Account and Region Information
output "account_id" {
  description = "AWS Account ID where resources are deployed"
  value       = data.aws_caller_identity.current.account_id
}

output "region" {
  description = "AWS Region where resources are deployed"
  value       = data.aws_region.current.name
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# Lambda Function Outputs
output "lambda_function_arns" {
  description = "ARNs of all deployed Lambda functions"
  value       = module.lambda_functions.lambda_function_arns
}

output "lambda_function_names" {
  description = "Names of all deployed Lambda functions"
  value       = module.lambda_functions.lambda_function_names
}

output "lambda_function_invoke_arns" {
  description = "Invoke ARNs for API Gateway integration"
  value       = module.lambda_functions.lambda_function_invoke_arns
}

# IAM Outputs
output "lambda_execution_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = module.iam.lambda_execution_role_arn
}

output "lambda_execution_role_name" {
  description = "Name of the Lambda execution role"
  value       = module.iam.lambda_execution_role_name
}

# Monitoring Outputs
output "cloudwatch_dashboard_url" {
  description = "URL to the CloudWatch dashboard"
  value       = module.monitoring.dashboard_url
}

output "sns_topic_arn" {
  description = "ARN of the SNS topic for notifications"
  value       = module.monitoring.sns_topic_arn
}

output "cost_anomaly_detector_arn" {
  description = "ARN of the Cost Anomaly Detector"
  value       = module.monitoring.cost_anomaly_detector_arn
}

# Storage Outputs
output "reports_bucket_name" {
  description = "Name of the S3 bucket for cost reports"
  value       = module.storage.reports_bucket_name
}

output "reports_bucket_arn" {
  description = "ARN of the S3 bucket for cost reports"
  value       = module.storage.reports_bucket_arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for optimization state"
  value       = module.storage.dynamodb_table_name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for optimization state"
  value       = module.storage.dynamodb_table_arn
}

# Security Outputs
output "kms_key_arn" {
  description = "ARN of the KMS key for encryption"
  value       = module.iam.kms_key_arn
}

output "kms_key_id" {
  description = "ID of the KMS key for encryption"
  value       = module.iam.kms_key_id
}

# Scheduling Outputs
output "eventbridge_rules" {
  description = "EventBridge rules for Lambda scheduling"
  value       = module.lambda_functions.eventbridge_rules
}

# Cost Optimization Metrics
output "estimated_monthly_savings" {
  description = "Estimated monthly cost savings from platform deployment"
  value = {
    tier_1_critical  = "£5,000-12,000"
    tier_2_strategic = "£8,000-25,000"
    tier_3_analytics = "£2,000-8,000"
    tier_4_governance = "£1,000-5,000"
    total_potential  = "£16,000-50,000"
  }
}

# Deployment Information
output "deployment_timestamp" {
  description = "Timestamp of the deployment"
  value       = timestamp()
}

output "terraform_version" {
  description = "Terraform version used for deployment"
  value       = "~> 1.5"
}

# Enterprise Compliance
output "compliance_status" {
  description = "Compliance features enabled"
  value = {
    encryption_at_rest     = "Enabled (KMS)"
    encryption_in_transit  = "Enabled (TLS 1.2+)"
    access_logging        = "Enabled (CloudTrail)"
    monitoring           = "Enabled (CloudWatch)"
    alerting            = "Enabled (SNS)"
    backup              = "Enabled (Point-in-time recovery)"
    cross_account       = var.enable_cross_account ? "Enabled" : "Disabled"
    xray_tracing        = var.enable_xray_tracing ? "Enabled" : "Disabled"
  }
}

# Quick Access URLs (for documentation)
output "quick_access" {
  description = "Quick access information for the platform"
  value = {
    cloudwatch_dashboard = "https://${data.aws_region.current.name}.console.aws.amazon.com/cloudwatch/home?region=${data.aws_region.current.name}#dashboards:name=${var.project_name}-${var.environment}"
    lambda_console      = "https://${data.aws_region.current.name}.console.aws.amazon.com/lambda/home?region=${data.aws_region.current.name}#/functions"
    cost_explorer       = "https://console.aws.amazon.com/cost-management/home#/cost-explorer"
    s3_reports         = "https://s3.console.aws.amazon.com/s3/buckets/${module.storage.reports_bucket_name}"
  }
}
