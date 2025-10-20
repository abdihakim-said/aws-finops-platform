# Lambda Module - All FinOps Functions

# Package Lambda functions
data "archive_file" "lambda_packages" {
  for_each = var.lambda_functions

  type        = "zip"
  source_file = "${path.module}/../../../lambda-functions/${each.value.source_file}"
  output_path = "${path.module}/packages/${each.key}.zip"
}

# Create packages directory
resource "null_resource" "create_packages_dir" {
  provisioner "local-exec" {
    command = "mkdir -p ${path.module}/packages"
  }
}

# Deploy all Lambda functions
resource "aws_lambda_function" "finops_functions" {
  for_each = var.lambda_functions

  filename         = data.archive_file.lambda_packages[each.key].output_path
  function_name    = "${var.environment}-${each.key}"
  role            = var.lambda_execution_role_arn
  handler         = each.value.handler
  runtime         = var.runtime
  timeout         = each.value.timeout
  memory_size     = each.value.memory_size
  source_code_hash = data.archive_file.lambda_packages[each.key].output_base64sha256

  environment {
    variables = merge(
      var.common_env_vars,
      each.value.env_vars
    )
  }

  tracing_config {
    mode = "Active"
  }

  tags = merge(
    var.common_tags,
    {
      Name     = "${var.environment}-${each.key}"
      Function = each.key
      Tier     = each.value.tier
    }
  )

  depends_on = [null_resource.create_packages_dir]
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "lambda_logs" {
  for_each = var.lambda_functions

  name              = "/aws/lambda/${aws_lambda_function.finops_functions[each.key].function_name}"
  retention_in_days = 30

  tags = var.common_tags
}

# EventBridge Rules for scheduling
resource "aws_cloudwatch_event_rule" "lambda_schedules" {
  for_each = var.lambda_schedules

  name                = "${var.environment}-${each.key}-schedule"
  description         = "Schedule for ${each.key} function"
  schedule_expression = each.value

  tags = var.common_tags
}

# EventBridge Targets
resource "aws_cloudwatch_event_target" "lambda_targets" {
  for_each = var.lambda_schedules

  rule      = aws_cloudwatch_event_rule.lambda_schedules[each.key].name
  target_id = "${each.key}Target"
  arn       = aws_lambda_function.finops_functions[each.key].arn
}

# Lambda permissions for EventBridge
resource "aws_lambda_permission" "allow_eventbridge" {
  for_each = var.lambda_schedules

  statement_id  = "AllowExecutionFromEventBridge-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finops_functions[each.key].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_schedules[each.key].arn
}

# Lambda function aliases for blue/green deployments
resource "aws_lambda_alias" "function_aliases" {
  for_each = var.lambda_functions

  name             = "live"
  description      = "Live alias for ${each.key}"
  function_name    = aws_lambda_function.finops_functions[each.key].function_name
  function_version = "$LATEST"
}
