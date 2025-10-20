# Storage Module - S3 and DynamoDB for FinOps Platform

# S3 Bucket for cost reports and data
resource "aws_s3_bucket" "finops_reports" {
  bucket = "${var.project_name}-${var.environment}-reports-${random_id.bucket_suffix.hex}"

  tags = var.common_tags
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# S3 Bucket versioning
resource "aws_s3_bucket_versioning" "finops_reports_versioning" {
  bucket = aws_s3_bucket.finops_reports.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "finops_reports_encryption" {
  bucket = aws_s3_bucket.finops_reports.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket public access block
resource "aws_s3_bucket_public_access_block" "finops_reports_pab" {
  bucket = aws_s3_bucket.finops_reports.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket lifecycle configuration
resource "aws_s3_bucket_lifecycle_configuration" "finops_reports_lifecycle" {
  bucket = aws_s3_bucket.finops_reports.id

  rule {
    id     = "cost_reports_lifecycle"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 365
    }

    noncurrent_version_expiration {
      noncurrent_days = 90
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }
  }
}

# DynamoDB table for optimization state
resource "aws_dynamodb_table" "finops_state" {
  name           = "${var.project_name}-${var.environment}-optimization-state"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "resource_id"
  range_key      = "optimization_type"

  attribute {
    name = "resource_id"
    type = "S"
  }

  attribute {
    name = "optimization_type"
    type = "S"
  }

  attribute {
    name = "last_optimized"
    type = "S"
  }

  global_secondary_index {
    name               = "LastOptimizedIndex"
    hash_key           = "optimization_type"
    range_key          = "last_optimized"
    projection_type    = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = var.common_tags
}

# DynamoDB table for savings tracking
resource "aws_dynamodb_table" "finops_savings" {
  name           = "${var.project_name}-${var.environment}-savings-tracking"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "date"
  range_key      = "optimization_type"

  attribute {
    name = "date"
    type = "S"
  }

  attribute {
    name = "optimization_type"
    type = "S"
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = var.common_tags
}
