output "reports_bucket_name" {
  description = "Name of the S3 reports bucket"
  value       = aws_s3_bucket.finops_reports.bucket
}

output "reports_bucket_arn" {
  description = "ARN of the S3 reports bucket"
  value       = aws_s3_bucket.finops_reports.arn
}

output "dynamodb_table_name" {
  description = "Name of the DynamoDB optimization state table"
  value       = aws_dynamodb_table.finops_state.name
}

output "dynamodb_table_arn" {
  description = "ARN of the DynamoDB optimization state table"
  value       = aws_dynamodb_table.finops_state.arn
}

output "savings_table_name" {
  description = "Name of the DynamoDB savings tracking table"
  value       = aws_dynamodb_table.finops_savings.name
}

output "savings_table_arn" {
  description = "ARN of the DynamoDB savings tracking table"
  value       = aws_dynamodb_table.finops_savings.arn
}
