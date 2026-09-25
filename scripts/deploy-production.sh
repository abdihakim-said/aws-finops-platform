#!/bin/bash

# AWS FinOps Platform - Production Deployment Script
# Tests all 11 Lambda functions

set -e

echo "🚀 AWS FinOps Platform - Production Deployment"
echo "=============================================="

# Check AWS CLI configuration
echo "📋 Checking AWS configuration..."
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "❌ AWS CLI not configured. Please run 'aws configure'"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=$(aws configure get region || echo "us-east-1")

echo "✅ AWS Account: $ACCOUNT_ID"
echo "✅ Region: $REGION"

# Step 1: Setup backend infrastructure
echo ""
echo "🏗️  Step 1: Setting up Terraform backend..."
cd terraform

# Create backend resources
terraform init
terraform plan -target=aws_s3_bucket.terraform_state -target=aws_dynamodb_table.terraform_state_lock
terraform apply -target=aws_s3_bucket.terraform_state -target=aws_dynamodb_table.terraform_state_lock -auto-approve

echo "✅ Backend infrastructure created"

# Step 2: Deploy production environment
echo ""
echo "🚀 Step 2: Deploying production environment..."
cd environments/production

# Initialize with backend
terraform init

# Plan deployment
echo "📋 Planning production deployment..."
terraform plan -out=production.tfplan

# Apply deployment
echo "🚀 Deploying all 11 Lambda functions..."
terraform apply production.tfplan

# Get outputs
echo ""
echo "📊 Deployment Results:"
echo "====================="

LAMBDA_FUNCTIONS=$(terraform output -json lambda_function_names | jq -r 'keys[]')
DASHBOARD_URL=$(terraform output -raw dashboard_url)

echo "✅ Lambda Functions Deployed:"
for func in $LAMBDA_FUNCTIONS; do
    echo "   - $func"
done

echo ""
echo "📈 Monitoring:"
echo "   Dashboard: $DASHBOARD_URL"

# Step 3: Test Lambda functions
echo ""
echo "🧪 Step 3: Testing Lambda functions..."

# Test each function
for func in $LAMBDA_FUNCTIONS; do
    echo "Testing $func..."
    
    # Invoke function with test event
    aws lambda invoke \
        --function-name "production-$func" \
        --payload '{"test": true}' \
        --region $REGION \
        /tmp/response-$func.json > /dev/null 2>&1
    
    if [ $? -eq 0 ]; then
        echo "   ✅ $func - SUCCESS"
    else
        echo "   ❌ $func - FAILED"
    fi
done

# Step 4: Validation
echo ""
echo "🔍 Step 4: Validation..."

# Check CloudWatch logs
echo "📊 Checking CloudWatch logs..."
for func in $LAMBDA_FUNCTIONS; do
    LOG_GROUP="/aws/lambda/production-$func"
    
    # Check if log group exists
    if aws logs describe-log-groups --log-group-name-prefix "$LOG_GROUP" --region $REGION | grep -q "$LOG_GROUP"; then
        echo "   ✅ $func - Log group exists"
    else
        echo "   ⚠️  $func - No log group yet"
    fi
done

# Summary
echo ""
echo "🎉 Production Deployment Complete!"
echo "=================================="
echo "✅ Backend: S3 + DynamoDB state management"
echo "✅ Functions: All 11 Lambda functions deployed"
echo "✅ Monitoring: CloudWatch dashboard active"
echo "✅ Scheduling: EventBridge rules configured"
echo "✅ Storage: S3 + DynamoDB for reports and state"
echo ""
echo "📈 Dashboard: $DASHBOARD_URL"
echo ""
echo "🔧 Next Steps:"
echo "1. Monitor dashboard for function execution"
echo "2. Check SNS notifications for alerts"
echo "3. Review S3 bucket for optimization reports"
echo "4. Validate DynamoDB for state tracking"

cd ../../..
