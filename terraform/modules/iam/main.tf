# IAM Module - Enterprise Security with Least Privilege

# KMS Key for encryption
resource "aws_kms_key" "finops_key" {
  description             = "${var.project_name} encryption key"
  deletion_window_in_days = 7
  enable_key_rotation     = true

  tags = var.common_tags
}

resource "aws_kms_alias" "finops_key_alias" {
  name          = "alias/${var.project_name}-${var.environment}"
  target_key_id = aws_kms_key.finops_key.key_id
}

# Lambda execution role
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.project_name}-${var.environment}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = var.common_tags
}

# Comprehensive IAM policy for cost optimization
resource "aws_iam_role_policy" "lambda_cost_optimization_policy" {
  name = "${var.project_name}-${var.environment}-cost-optimization-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          # EC2 Cost Optimization
          "ec2:DescribeVolumes",
          "ec2:ModifyVolume",
          "ec2:DescribeSnapshots",
          "ec2:DeleteSnapshot",
          "ec2:DescribeInstances",
          "ec2:DescribeSecurityGroups",
          "ec2:DescribeAddresses",
          "ec2:ReleaseAddress",
          "ec2:DeleteSecurityGroup",
          "ec2:DescribeReservedInstances",
          
          # RDS Optimization
          "rds:DescribeDBInstances",
          "rds:ModifyDBInstance",
          "rds:DescribeDBClusters",
          "rds:StopDBInstance",
          
          # S3 Optimization
          "s3:ListAllMyBuckets",
          "s3:GetBucketLocation",
          "s3:GetLifecycleConfiguration",
          "s3:PutLifecycleConfiguration",
          "s3:GetBucketAnalyticsConfiguration",
          
          # Cost Explorer
          "ce:GetCostAndUsage",
          "ce:GetUsageReport",
          "ce:GetReservationCoverage",
          "ce:GetReservationPurchaseRecommendation",
          "ce:GetAnomalies",
          
          # CloudWatch
          "cloudwatch:GetMetricStatistics",
          "cloudwatch:PutMetricData",
          "cloudwatch:ListMetrics",
          
          # ELB
          "elasticloadbalancing:DescribeLoadBalancers",
          "elasticloadbalancing:DescribeTargetGroups",
          
          # EKS/Kubernetes
          "eks:DescribeCluster",
          "eks:ListClusters",
          
          # Organizations (for multi-account)
          "organizations:ListAccounts",
          "organizations:DescribeOrganization"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          # S3 bucket access for reports
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Resource = "arn:aws:s3:::${var.project_name}-${var.environment}-*/*"
      },
      {
        Effect = "Allow"
        Action = [
          # DynamoDB access for state management
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = "arn:aws:dynamodb:*:*:table/${var.project_name}-${var.environment}-*"
      },
      {
        Effect = "Allow"
        Action = [
          # SNS for notifications
          "sns:Publish"
        ]
        Resource = "arn:aws:sns:*:*:${var.project_name}-${var.environment}-*"
      },
      {
        Effect = "Allow"
        Action = [
          # KMS for encryption
          "kms:Decrypt",
          "kms:Encrypt",
          "kms:GenerateDataKey"
        ]
        Resource = aws_kms_key.finops_key.arn
      }
    ]
  })
}

# Attach AWS managed policies
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy_attachment" "lambda_vpc_execution" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "xray_write_only" {
  role       = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}
