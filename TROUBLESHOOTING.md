# AWS FinOps Platform - Troubleshooting Guide

## 🚨 Common Issues & Solutions

### 1. CloudWatch Dashboard Shows "No Data Available"

**Symptoms:**
- Dashboard widgets display "No data available"
- Metrics appear empty despite successful deployment

**Root Causes & Solutions:**

#### Time Range Issues
```bash
# Check function schedules
aws events list-rules --name-prefix production- --region us-east-1

# Verify last invocation
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/production-" --region us-east-1
```

**Fix:** Extend dashboard time range to 24-48 hours

#### Functions Not Triggered
```bash
# Manual test invocation
aws lambda invoke --function-name production-cost-optimizer \
  --invocation-type RequestResponse /tmp/response.json --region us-east-1

# Check invocation metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Invocations \
  --dimensions Name=FunctionName,Value=production-cost-optimizer \
  --start-time 2025-10-19T00:00:00Z \
  --end-time 2025-10-21T00:00:00Z \
  --period 3600 \
  --statistics Sum --region us-east-1
```

### 2. Lambda Function Deployment Hangs

**Symptoms:**
- Functions stuck in "Pending" state for 45+ minutes
- Terraform deployment times out

**Root Causes:**
- AWS Lambda service internal errors
- VPC configuration issues
- IAM permission delays

**Solutions:**

#### Immediate Fix
```bash
# Delete stuck functions
aws lambda delete-function --function-name STUCK_FUNCTION_NAME --region us-east-1

# Clear Terraform state lock
rm -f terraform/.terraform/terraform.tfstate.lock.info

# Retry deployment
terraform apply -auto-approve
```

#### Prevention
```bash
# Add timeout to Terraform Lambda resources
resource "aws_lambda_function" "example" {
  timeout = 300  # 5 minutes max
  
  lifecycle {
    create_before_destroy = true
  }
}
```

### 3. Cost Explorer Anomaly Detection Errors

**Symptoms:**
- Terraform fails with Cost Explorer configuration errors
- Invalid dimension or threshold syntax

**Common Fixes:**

#### Dimension Configuration
```hcl
# Correct format
dimension_key = "LINKED_ACCOUNT"
dimension_value_match_options = ["EQUALS"]
dimension_match_options = ["EQUALS"]
```

#### Threshold Expression
```hcl
# Simplified threshold
threshold_expression {
  and {
    dimension {
      key           = "LINKED_ACCOUNT"
      values        = [data.aws_caller_identity.current.account_id]
      match_options = ["EQUALS"]
    }
  }
}
```

### 4. EventBridge Schedule Not Triggering

**Symptoms:**
- Functions deployed but never execute
- No CloudWatch logs generated

**Diagnostic Commands:**
```bash
# Check rule status
aws events describe-rule --name production-cost-optimizer-schedule --region us-east-1

# List targets
aws events list-targets-by-rule --rule production-cost-optimizer-schedule --region us-east-1

# Check permissions
aws lambda get-policy --function-name production-cost-optimizer --region us-east-1
```

**Fix Missing Permissions:**
```bash
aws lambda add-permission \
  --function-name production-cost-optimizer \
  --statement-id allow-eventbridge \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:ACCOUNT:rule/production-cost-optimizer-schedule \
  --region us-east-1
```

### 5. IAM Permission Errors

**Symptoms:**
- Functions fail with "AccessDenied" errors
- Unable to access AWS services

**Quick Permission Check:**
```bash
# Test function permissions
aws sts get-caller-identity

# Check role policies
aws iam list-attached-role-policies --role-name aws-finops-platform-production-lambda-role

# Test specific service access
aws ec2 describe-instances --max-items 1 --region us-east-1
```

## 🔧 Diagnostic Commands

### Health Check Script
```bash
#!/bin/bash
echo "=== AWS FinOps Platform Health Check ==="

# 1. Check Lambda functions
echo "Lambda Functions:"
aws lambda list-functions --query 'Functions[?contains(FunctionName, `production-`)].{Name:FunctionName,Status:State}' --output table --region us-east-1

# 2. Check EventBridge rules
echo "EventBridge Rules:"
aws events list-rules --name-prefix production- --query 'Rules[].{Name:Name,State:State,Schedule:ScheduleExpression}' --output table --region us-east-1

# 3. Check recent invocations
echo "Recent Invocations (last 24h):"
aws logs describe-log-groups --log-group-name-prefix "/aws/lambda/production-" --query 'logGroups[].{Function:logGroupName,LastEvent:lastEventTime}' --output table --region us-east-1

# 4. Check CloudWatch dashboard
echo "Dashboard Status:"
aws cloudwatch list-dashboards --query 'DashboardEntries[?contains(DashboardName, `finops`)].DashboardName' --output table --region us-east-1
```

### Performance Monitoring
```bash
# Function duration metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=production-cost-optimizer \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Average,Maximum --region us-east-1

# Error rate check
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=production-cost-optimizer \
  --start-time $(date -u -d '24 hours ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 3600 \
  --statistics Sum --region us-east-1
```

## 📋 Maintenance Checklist

### Daily Checks
- [ ] Review CloudWatch dashboard for anomalies
- [ ] Check Lambda error rates
- [ ] Verify cost optimization alerts

### Weekly Checks
- [ ] Review function execution logs
- [ ] Validate cost savings reports
- [ ] Check EventBridge rule health

### Monthly Checks
- [ ] Update Lambda function code if needed
- [ ] Review IAM permissions
- [ ] Analyze cost optimization effectiveness
- [ ] Update documentation

## 🆘 Emergency Procedures

### Complete System Reset
```bash
# 1. Stop all schedules
aws events list-rules --name-prefix production- --query 'Rules[].Name' --output text | \
xargs -I {} aws events disable-rule --name {} --region us-east-1

# 2. Clear stuck deployments
terraform destroy -auto-approve

# 3. Clean state
rm -rf .terraform/
rm terraform.tfstate*

# 4. Fresh deployment
terraform init
terraform plan
terraform apply -auto-approve
```

### Rollback Procedure
```bash
# 1. Identify last working state
git log --oneline -10

# 2. Revert to working commit
git checkout WORKING_COMMIT_HASH

# 3. Redeploy
terraform apply -auto-approve

# 4. Verify functionality
./health-check.sh
```

## 📞 Support Contacts

- **AWS Support:** Use AWS Support Center for service-level issues
- **Internal Team:** Contact DevOps team for deployment issues
- **Documentation:** Refer to AWS Lambda, EventBridge, and CloudWatch documentation

---
*Last Updated: October 2025*
