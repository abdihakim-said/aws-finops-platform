output "sns_topic_arn" {
  description = "ARN of the SNS topic"
  value       = aws_sns_topic.finops_notifications.arn
}

output "dashboard_url" {
  description = "URL of the CloudWatch dashboard"
  value       = "https://console.aws.amazon.com/cloudwatch/home#dashboards:name=${aws_cloudwatch_dashboard.finops_dashboard.dashboard_name}"
}

output "cost_anomaly_detector_arn" {
  description = "ARN of the cost anomaly monitor"
  value       = aws_ce_anomaly_monitor.finops_anomaly_monitor.arn
}
