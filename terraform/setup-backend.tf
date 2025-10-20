# Backend Infrastructure Setup - Run this first

# S3 bucket for Terraform state
resource "aws_s3_bucket" "terraform_state" {
  bucket = "finops-platform-terraform-state-prod"

  tags = {
    Name        = "Terraform State Bucket"
    Environment = "production"
    Purpose     = "terraform-state"
  }
}

# S3 bucket versioning
resource "aws_s3_bucket_versioning" "terraform_state_versioning" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

# S3 bucket encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state_encryption" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 bucket public access block
resource "aws_s3_bucket_public_access_block" "terraform_state_pab" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# DynamoDB table for state locking
resource "aws_dynamodb_table" "terraform_state_lock" {
  name           = "finops-terraform-state-lock"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = "Terraform State Lock Table"
    Environment = "production"
    Purpose     = "terraform-state-lock"
  }
}

# Backend-specific outputs
output "backend_s3_bucket" {
  description = "S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.bucket
}

output "backend_dynamodb_table" {
  description = "DynamoDB table for state locking"
  value       = aws_dynamodb_table.terraform_state_lock.name
}
