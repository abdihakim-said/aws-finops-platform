# Monitoring Module - CloudWatch Dashboards, Alarms, SNS

# SNS Topic for notifications
resource "aws_sns_topic" "finops_notifications" {
  name = "${var.project_name}-${var.environment}-notifications"

  tags = var.common_tags
}

# SNS Topic Subscription
resource "aws_sns_topic_subscription" "email_notification" {
  topic_arn = aws_sns_topic.finops_notifications.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "finops_dashboard" {
  dashboard_name = "${var.project_name}-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6

        properties = {
          metrics = [
            ["CostOptimization", "VolumesOptimized"],
            ["CostOptimization", "SnapshotsDeleted"],
            ["CostOptimization", "EstimatedMonthlySavings"]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "Cost Optimization Metrics"
          period  = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6

        properties = {
          metrics = [
            for func_name in keys(var.lambda_function_arns) : [
              "AWS/Lambda", "Duration", "FunctionName", "${var.environment}-${func_name}"
            ]
          ]
          view    = "timeSeries"
          stacked = false
          region  = "us-east-1"
          title   = "Lambda Function Performance"
          period  = 300
        }
      }
    ]
  })
}

# Cost Anomaly Monitor (correct syntax)
resource "aws_ce_anomaly_monitor" "finops_anomaly_monitor" {
  name         = "${var.project_name}-${var.environment}-anomaly-monitor"
  monitor_type = "CUSTOM"

  monitor_specification = jsonencode({
    Dimensions = {
      Key          = "LINKED_ACCOUNT"
      Values       = ["880385175593"]
      MatchOptions = ["EQUALS"]
    }
  })

  tags = var.common_tags
}

# Cost Anomaly Subscription (correct resource name)
resource "aws_ce_anomaly_subscription" "finops_anomaly_subscription" {
  name      = "${var.project_name}-${var.environment}-anomaly-subscription"
  frequency = "DAILY"
  
  monitor_arn_list = [
    aws_ce_anomaly_monitor.finops_anomaly_monitor.arn
  ]
  
  subscriber {
    type    = "EMAIL"
    address = var.notification_email
  }

  threshold_expression {
    dimension {
      key           = "ANOMALY_TOTAL_IMPACT_ABSOLUTE"
      values        = [tostring(var.cost_threshold)]
      match_options = ["GREATER_THAN_OR_EQUAL"]
    }
  }

  tags = var.common_tags
}

# CloudWatch Alarms for Lambda functions
resource "aws_cloudwatch_metric_alarm" "lambda_error_alarm" {
  for_each = var.lambda_function_arns

  alarm_name          = "${var.environment}-${each.key}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This metric monitors lambda errors for ${each.key}"
  alarm_actions       = [aws_sns_topic.finops_notifications.arn]

  dimensions = {
    FunctionName = "${var.environment}-${each.key}"
  }

  tags = var.common_tags
}

# CloudWatch Alarms for Lambda duration
resource "aws_cloudwatch_metric_alarm" "lambda_duration_alarm" {
  for_each = var.lambda_function_arns

  alarm_name          = "${var.environment}-${each.key}-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Average"
  threshold           = "60000" # 1 minute
  alarm_description   = "This metric monitors lambda duration for ${each.key}"
  alarm_actions       = [aws_sns_topic.finops_notifications.arn]

  dimensions = {
    FunctionName = "${var.environment}-${each.key}"
  }

  tags = var.common_tags
}
