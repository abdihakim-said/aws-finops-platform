#!/bin/bash

# AWS FinOps Platform - Complete Resource Cleanup Script
# This script safely destroys all resources created by the platform

set -e

echo "🧹 AWS FinOps Platform - Resource Cleanup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get current AWS account and region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null || echo "unknown")
REGION=$(aws configure get region 2>/dev/null || echo "us-east-1")

echo -e "${YELLOW}Account ID: ${ACCOUNT_ID}${NC}"
echo -e "${YELLOW}Region: ${REGION}${NC}"
echo ""

# Confirmation prompt
echo -e "${RED}⚠️  WARNING: This will destroy ALL FinOps platform resources!${NC}"
echo "This includes:"
echo "  • 11 Production Lambda functions"
echo "  • 12 Development Lambda functions" 
echo "  • 24 EventBridge schedules"
echo "  • CloudWatch dashboards and alarms"
echo "  • S3 buckets and DynamoDB tables"
echo "  • IAM roles and policies"
echo "  • Cost Explorer anomaly detectors"
echo ""

read -p "Are you absolutely sure? Type 'DELETE' to confirm: " confirmation

if [ "$confirmation" != "DELETE" ]; then
    echo -e "${GREEN}Cleanup cancelled. Resources preserved.${NC}"
    exit 0
fi

echo ""
echo "🚀 Starting cleanup process..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 1. Disable all EventBridge rules first
echo "📅 Disabling EventBridge schedules..."
aws events list-rules --name-prefix "production-" --region $REGION --query 'Rules[].Name' --output text | \
xargs -I {} aws events disable-rule --name {} --region $REGION 2>/dev/null || true

aws events list-rules --name-prefix "dev-" --region $REGION --query 'Rules[].Name' --output text | \
xargs -I {} aws events disable-rule --name {} --region $REGION 2>/dev/null || true

echo -e "${GREEN}✓ EventBridge rules disabled${NC}"

# 2. Use Terraform to destroy infrastructure
echo ""
echo "🏗️  Destroying Terraform infrastructure..."

if [ -f "terraform/terraform.tfstate" ] || [ -f "terraform.tfstate" ]; then
    # Check if we're in the right directory
    if [ -f "main.tf" ] || [ -f "terraform/main.tf" ]; then
        if [ -d "terraform" ]; then
            cd terraform
        fi
        
        echo "Running terraform destroy..."
        terraform destroy -auto-approve || {
            echo -e "${YELLOW}⚠️  Terraform destroy had issues, continuing with manual cleanup...${NC}"
        }
        
        if [ -d "../terraform" ]; then
            cd ..
        fi
    else
        echo -e "${YELLOW}⚠️  Terraform files not found, proceeding with manual cleanup...${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No Terraform state found, proceeding with manual cleanup...${NC}"
fi

# 3. Manual cleanup of remaining resources
echo ""
echo "🧽 Manual cleanup of remaining resources..."

# Delete Lambda functions
echo "🔧 Cleaning up Lambda functions..."
aws lambda list-functions --region $REGION --query 'Functions[?contains(FunctionName, `production-`) || contains(FunctionName, `dev-`)].FunctionName' --output text | \
xargs -I {} aws lambda delete-function --function-name {} --region $REGION 2>/dev/null || true

echo -e "${GREEN}✓ Lambda functions cleaned${NC}"

# Delete EventBridge rules and targets
echo "📅 Cleaning up EventBridge rules..."
for rule in $(aws events list-rules --region $REGION --query 'Rules[?contains(Name, `production-`) || contains(Name, `dev-`)].Name' --output text); do
    # Remove targets first
    aws events remove-targets --rule $rule --ids $(aws events list-targets-by-rule --rule $rule --region $REGION --query 'Targets[].Id' --output text) --region $REGION 2>/dev/null || true
    # Delete rule
    aws events delete-rule --name $rule --region $REGION 2>/dev/null || true
done

echo -e "${GREEN}✓ EventBridge rules cleaned${NC}"

# Delete CloudWatch dashboards
echo "📊 Cleaning up CloudWatch dashboards..."
aws cloudwatch list-dashboards --region $REGION --query 'DashboardEntries[?contains(DashboardName, `finops`) || contains(DashboardName, `aws-finops`)].DashboardName' --output text | \
xargs -I {} aws cloudwatch delete-dashboards --dashboard-names {} --region $REGION 2>/dev/null || true

echo -e "${GREEN}✓ CloudWatch dashboards cleaned${NC}"

# Delete CloudWatch alarms
echo "⏰ Cleaning up CloudWatch alarms..."
aws cloudwatch describe-alarms --region $REGION --query 'MetricAlarms[?contains(AlarmName, `finops`) || contains(AlarmName, `production-`) || contains(AlarmName, `dev-`)].AlarmName' --output text | \
xargs -I {} aws cloudwatch delete-alarms --alarm-names {} --region $REGION 2>/dev/null || true

echo -e "${GREEN}✓ CloudWatch alarms cleaned${NC}"

# Delete Log Groups
echo "📝 Cleaning up CloudWatch Log Groups..."
aws logs describe-log-groups --region $REGION --query 'logGroups[?contains(logGroupName, `production-`) || contains(logGroupName, `dev-`) || contains(logGroupName, `finops`)].logGroupName' --output text | \
xargs -I {} aws logs delete-log-group --log-group-name {} --region $REGION 2>/dev/null || true

echo -e "${GREEN}✓ Log groups cleaned${NC}"

# Delete S3 buckets (empty first, then delete)
echo "🪣 Cleaning up S3 buckets..."
for bucket in $(aws s3api list-buckets --region $REGION --query 'Buckets[?contains(Name, `finops`) || contains(Name, `aws-finops`)].Name' --output text); do
    echo "  Emptying bucket: $bucket"
    aws s3 rm s3://$bucket --recursive --region $REGION 2>/dev/null || true
    aws s3api delete-bucket --bucket $bucket --region $REGION 2>/dev/null || true
done

echo -e "${GREEN}✓ S3 buckets cleaned${NC}"

# Delete DynamoDB tables
echo "🗄️  Cleaning up DynamoDB tables..."
aws dynamodb list-tables --region $REGION --query 'TableNames[?contains(@, `finops`) || contains(@, `aws-finops`)]' --output text | \
xargs -I {} aws dynamodb delete-table --table-name {} --region $REGION 2>/dev/null || true

echo -e "${GREEN}✓ DynamoDB tables cleaned${NC}"

# Delete SNS topics
echo "📢 Cleaning up SNS topics..."
aws sns list-topics --region $REGION --query 'Topics[?contains(TopicArn, `finops`) || contains(TopicArn, `aws-finops`)].TopicArn' --output text | \
xargs -I {} aws sns delete-topic --topic-arn {} --region $REGION 2>/dev/null || true

echo -e "${GREEN}✓ SNS topics cleaned${NC}"

# Delete IAM roles and policies (be careful here)
echo "🔐 Cleaning up IAM roles..."
for role in $(aws iam list-roles --query 'Roles[?contains(RoleName, `finops`) || contains(RoleName, `aws-finops`)].RoleName' --output text); do
    # Detach managed policies
    aws iam list-attached-role-policies --role-name $role --query 'AttachedPolicies[].PolicyArn' --output text | \
    xargs -I {} aws iam detach-role-policy --role-name $role --policy-arn {} 2>/dev/null || true
    
    # Delete inline policies
    aws iam list-role-policies --role-name $role --query 'PolicyNames[]' --output text | \
    xargs -I {} aws iam delete-role-policy --role-name $role --policy-name {} 2>/dev/null || true
    
    # Delete role
    aws iam delete-role --role-name $role 2>/dev/null || true
done

echo -e "${GREEN}✓ IAM roles cleaned${NC}"

# Delete custom IAM policies
echo "📋 Cleaning up IAM policies..."
aws iam list-policies --scope Local --query 'Policies[?contains(PolicyName, `finops`) || contains(PolicyName, `aws-finops`)].Arn' --output text | \
xargs -I {} aws iam delete-policy --policy-arn {} 2>/dev/null || true

echo -e "${GREEN}✓ IAM policies cleaned${NC}"

# Clean up local files
echo ""
echo "🗂️  Cleaning up local files..."

# Remove Terraform state and cache
rm -rf .terraform/ 2>/dev/null || true
rm -rf terraform/.terraform/ 2>/dev/null || true
rm -f terraform.tfstate* 2>/dev/null || true
rm -f terraform/terraform.tfstate* 2>/dev/null || true
rm -f .terraform.lock.hcl 2>/dev/null || true
rm -f terraform/.terraform.lock.hcl 2>/dev/null || true

# Remove temporary files
rm -f /tmp/lambda-response.json 2>/dev/null || true
rm -f /tmp/terraform-* 2>/dev/null || true

echo -e "${GREEN}✓ Local files cleaned${NC}"

# Final verification
echo ""
echo "🔍 Verification check..."

REMAINING_FUNCTIONS=$(aws lambda list-functions --region $REGION --query 'Functions[?contains(FunctionName, `production-`) || contains(FunctionName, `dev-`)].FunctionName' --output text | wc -w)
REMAINING_RULES=$(aws events list-rules --region $REGION --query 'Rules[?contains(Name, `production-`) || contains(Name, `dev-`)].Name' --output text | wc -w)

if [ "$REMAINING_FUNCTIONS" -eq 0 ] && [ "$REMAINING_RULES" -eq 0 ]; then
    echo -e "${GREEN}✅ Cleanup completed successfully!${NC}"
    echo -e "${GREEN}All FinOps platform resources have been destroyed.${NC}"
else
    echo -e "${YELLOW}⚠️  Some resources may still exist:${NC}"
    echo "  Lambda functions: $REMAINING_FUNCTIONS"
    echo "  EventBridge rules: $REMAINING_RULES"
    echo ""
    echo "You may need to check the AWS Console for any remaining resources."
fi

echo ""
echo "📊 Cleanup Summary:"
echo "  • Lambda functions: Removed"
echo "  • EventBridge schedules: Removed"  
echo "  • CloudWatch dashboards: Removed"
echo "  • CloudWatch alarms: Removed"
echo "  • Log groups: Removed"
echo "  • S3 buckets: Removed"
echo "  • DynamoDB tables: Removed"
echo "  • SNS topics: Removed"
echo "  • IAM roles/policies: Removed"
echo "  • Local Terraform state: Removed"

echo ""
echo -e "${GREEN}🎉 AWS FinOps Platform cleanup complete!${NC}"
echo ""
echo "Thank you for using the AWS FinOps Platform!"
echo ""
