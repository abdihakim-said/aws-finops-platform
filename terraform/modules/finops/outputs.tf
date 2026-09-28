output "plan_bucket" {
  value = aws_s3_bucket.plans.id
}

output "topic_arn" {
  value = aws_sns_topic.plans.arn
}

output "scan_function" {
  value = aws_lambda_function.scan.function_name
}

output "apply_function" {
  value = aws_lambda_function.apply.function_name
}

output "apply_command" {
  description = "Template for approving a plan from the email."
  value       = "aws lambda invoke --function-name ${aws_lambda_function.apply.function_name} --cli-binary-format raw-in-base64-out --payload '{\"plan_id\":\"<id>\",\"plan_digest\":\"<digest>\",\"approved_by\":\"<your name>\"}' out.json"
}
