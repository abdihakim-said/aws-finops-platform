output "lambda_function_arns" {
  description = "ARNs of all Lambda functions"
  value = {
    for name, func in aws_lambda_function.finops_functions : name => func.arn
  }
}

output "lambda_function_names" {
  description = "Names of all Lambda functions"
  value = {
    for name, func in aws_lambda_function.finops_functions : name => func.function_name
  }
}

output "lambda_function_invoke_arns" {
  description = "Invoke ARNs of all Lambda functions"
  value = {
    for name, func in aws_lambda_function.finops_functions : name => func.invoke_arn
  }
}

output "eventbridge_rules" {
  description = "EventBridge rule ARNs"
  value = {
    for name, rule in aws_cloudwatch_event_rule.lambda_schedules : name => rule.arn
  }
}

output "lambda_log_groups" {
  description = "CloudWatch log group ARNs"
  value = {
    for name, log_group in aws_cloudwatch_log_group.lambda_logs : name => log_group.arn
  }
}
