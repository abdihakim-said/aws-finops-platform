# Terraform Remote Backend Configuration
# S3 bucket for state storage with DynamoDB for state locking

terraform {
  backend "s3" {
    bucket         = "aws-finops-platform-terraform-state"
    key            = "finops/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "aws-finops-platform-terraform-locks"
    encrypt        = true
  }
}
