data "aws_region" "current" {}
data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  regions    = length(var.regions) > 0 ? var.regions : [data.aws_region.current.region]
  bucket     = "${var.name}-plans-${data.aws_caller_identity.current.account_id}-${data.aws_region.current.region}"
  source_dir = "${path.module}/../../../finops"
  runtime    = "python3.12"
}

# ---- Package ------------------------------------------------------------------

data "archive_file" "package" {
  type        = "zip"
  output_path = "${path.module}/.build/finops.zip"

  dynamic "source" {
    for_each = fileset(local.source_dir, "*.py")
    content {
      content  = file("${local.source_dir}/${source.value}")
      filename = "finops/${source.value}"
    }
  }
}

# ---- Plan storage -------------------------------------------------------------

resource "aws_s3_bucket" "plans" {
  bucket = local.bucket
  tags   = var.tags
}

resource "aws_s3_bucket_ownership_controls" "plans" {
  bucket = aws_s3_bucket.plans.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "plans" {
  bucket                  = aws_s3_bucket.plans.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "plans" {
  bucket = aws_s3_bucket.plans.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "plans" {
  bucket = aws_s3_bucket.plans.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "plans" {
  bucket = aws_s3_bucket.plans.id

  rule {
    id     = "expire-old-plans-and-results"
    status = "Enabled"
    filter {}
    expiration {
      days = 180
    }
    noncurrent_version_expiration {
      noncurrent_days = 30
    }
    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }
}

data "aws_iam_policy_document" "plans_bucket" {
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.plans.arn, "${aws_s3_bucket.plans.arn}/*"]
    principals {
      type        = "*"
      identifiers = ["*"]
    }
    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "plans" {
  bucket = aws_s3_bucket.plans.id
  policy = data.aws_iam_policy_document.plans_bucket.json
}

# ---- Notifications ------------------------------------------------------------

resource "aws_sns_topic" "plans" {
  name              = "${var.name}-plans"
  kms_master_key_id = "alias/aws/sns"
  tags              = var.tags
}

resource "aws_sns_topic_subscription" "email" {
  count     = var.notification_email == null ? 0 : 1
  topic_arn = aws_sns_topic.plans.arn
  protocol  = "email"
  endpoint  = var.notification_email
}

# ---- IAM: scan (read-only) -------------------------------------------------------

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "aws_iam_policy_document" "scan" {
  statement {
    sid = "ReadOnlyDiscovery"
    actions = [
      "ec2:DescribeVolumes",
      "ec2:DescribeVolumesModifications",
      "ec2:DescribeSnapshots",
      "ec2:DescribeImages",
      "ec2:DescribeAddresses",
      "elasticloadbalancing:DescribeLoadBalancers",
      "rds:DescribeDBInstances",
      "cloudwatch:GetMetricStatistics",
      "compute-optimizer:GetEC2InstanceRecommendations",
      "s3:ListAllMyBuckets",
      "s3:GetBucketLocation",
      "s3:GetLifecycleConfiguration",
      "s3:ListBucketMultipartUploads",
    ]
    resources = ["*"]
  }
  statement {
    sid       = "WritePlans"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.plans.arn}/plans/*"]
  }
  statement {
    sid       = "NotifyApprovers"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.plans.arn]
  }
}

resource "aws_iam_role" "scan" {
  name               = "${var.name}-scan"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "scan" {
  role   = aws_iam_role.scan.id
  policy = data.aws_iam_policy_document.scan.json
}

resource "aws_iam_role_policy_attachment" "scan_logs" {
  role       = aws_iam_role.scan.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ---- IAM: apply (three write actions, never on finops:keep) ------------------------

data "aws_iam_policy_document" "apply" {
  statement {
    sid = "RecheckBeforeActing"
    actions = [
      "ec2:DescribeVolumes",
      "ec2:DescribeSnapshots",
      "ec2:DescribeImages",
      "ec2:DescribeAddresses",
    ]
    resources = ["*"]
  }
  statement {
    sid       = "PlannedActionsOnly"
    actions   = ["ec2:ModifyVolume", "ec2:DeleteSnapshot", "ec2:ReleaseAddress"]
    resources = ["*"]
  }
  statement {
    sid       = "NeverTouchKeptResources"
    effect    = "Deny"
    actions   = ["ec2:ModifyVolume", "ec2:DeleteSnapshot", "ec2:ReleaseAddress"]
    resources = ["*"]
    condition {
      test     = "StringEqualsIgnoreCase"
      variable = "aws:ResourceTag/finops:keep"
      values   = ["true"]
    }
  }
  statement {
    sid       = "ReadPlans"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.plans.arn}/plans/*"]
  }
  statement {
    sid       = "WriteResults"
    actions   = ["s3:PutObject"]
    resources = ["${aws_s3_bucket.plans.arn}/results/*"]
  }
}

resource "aws_iam_role" "apply" {
  name               = "${var.name}-apply"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
  tags               = var.tags
}

resource "aws_iam_role_policy" "apply" {
  role   = aws_iam_role.apply.id
  policy = data.aws_iam_policy_document.apply.json
}

resource "aws_iam_role_policy_attachment" "apply_logs" {
  role       = aws_iam_role.apply.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# ---- Functions -------------------------------------------------------------------

resource "aws_cloudwatch_log_group" "scan" {
  name              = "/aws/lambda/${var.name}-scan"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_cloudwatch_log_group" "apply" {
  name              = "/aws/lambda/${var.name}-apply"
  retention_in_days = var.log_retention_days
  tags              = var.tags
}

resource "aws_lambda_function" "scan" {
  function_name    = "${var.name}-scan"
  role             = aws_iam_role.scan.arn
  handler          = "finops.handlers.scan_handler"
  runtime          = local.runtime
  architectures    = ["arm64"]
  timeout          = 300
  memory_size      = 256
  filename         = data.archive_file.package.output_path
  source_code_hash = data.archive_file.package.output_base64sha256

  environment {
    variables = {
      PLAN_BUCKET           = aws_s3_bucket.plans.id
      TOPIC_ARN             = aws_sns_topic.plans.arn
      REGIONS               = join(",", local.regions)
      SNAPSHOT_MIN_AGE_DAYS = tostring(var.snapshot_min_age_days)
      IDLE_WINDOW_DAYS      = tostring(var.idle_window_days)
    }
  }

  depends_on = [aws_cloudwatch_log_group.scan]
  tags       = var.tags
}

resource "aws_lambda_function" "apply" {
  function_name    = "${var.name}-apply"
  role             = aws_iam_role.apply.arn
  handler          = "finops.handlers.apply_handler"
  runtime          = local.runtime
  architectures    = ["arm64"]
  timeout          = 300
  memory_size      = 256
  filename         = data.archive_file.package.output_path
  source_code_hash = data.archive_file.package.output_base64sha256

  environment {
    variables = {
      PLAN_BUCKET = aws_s3_bucket.plans.id
      ALLOW_APPLY = tostring(var.enable_apply)
    }
  }

  depends_on = [aws_cloudwatch_log_group.apply]
  tags       = var.tags
}

# ---- Schedule and alarm ---------------------------------------------------------------

resource "aws_cloudwatch_event_rule" "scan" {
  name                = "${var.name}-scan"
  schedule_expression = var.schedule
  tags                = var.tags
}

resource "aws_cloudwatch_event_target" "scan" {
  rule = aws_cloudwatch_event_rule.scan.name
  arn  = aws_lambda_function.scan.arn
}

resource "aws_lambda_permission" "scan_schedule" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.scan.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.scan.arn
}

resource "aws_cloudwatch_metric_alarm" "scan_errors" {
  alarm_name          = "${var.name}-scan-errors"
  alarm_description   = "The FinOps scan failed. No plan was produced."
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = aws_lambda_function.scan.function_name }
  statistic           = "Sum"
  period              = 3600
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.plans.arn]
  tags                = var.tags
}
