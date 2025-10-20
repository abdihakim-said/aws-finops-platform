# AWS FinOps Platform - Manual Implementation Guide

## Prerequisites
- AWS CLI configured with appropriate permissions
- Terraform installed (v1.0+)
- Python 3.9+
- Basic understanding of AWS services

## Step 1: Create Project Structure

```bash
mkdir aws-finops-platform
cd aws-finops-platform

# Create directory structure
mkdir -p {terraform/{modules/{iam,lambda,monitoring,storage},environments/{dev,staging,prod}},lambda-functions,scripts}
```

## Step 2: Lambda Functions Implementation

### 2.1 Core Cost Optimizer Function
Create `lambda-functions/cost_optimizer.py`:

```python
import json
import boto3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Main cost optimization orchestrator"""
    
    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')
    
    try:
        # Find unattached EBS volumes
        volumes = ec2.describe_volumes(
            Filters=[{'Name': 'status', 'Values': ['available']}]
        )
        
        optimized_count = 0
        total_savings = 0
        
        for volume in volumes['Volumes']:
            volume_id = volume['VolumeId']
            size = volume['Size']
            volume_type = volume['VolumeType']
            
            # Calculate potential savings (example: $0.10 per GB per month)
            monthly_cost = size * 0.10
            total_savings += monthly_cost
            
            logger.info(f"Found unattached volume {volume_id}: {size}GB, ${monthly_cost:.2f}/month")
            optimized_count += 1
        
        # Send metrics to CloudWatch
        cloudwatch.put_metric_data(
            Namespace='CostOptimization',
            MetricData=[
                {
                    'MetricName': 'VolumesOptimized',
                    'Value': optimized_count,
                    'Unit': 'Count'
                },
                {
                    'MetricName': 'EstimatedMonthlySavings',
                    'Value': total_savings,
                    'Unit': 'None'
                }
            ]
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Analyzed {optimized_count} volumes, potential savings: ${total_savings:.2f}/month'
            })
        }
        
    except Exception as e:
        logger.error(f"Error in cost optimization: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

### 2.2 EC2 Right-sizing Function
Create `lambda-functions/ec2_rightsizing.py`:

```python
import json
import boto3
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Analyze EC2 instances for right-sizing opportunities"""
    
    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')
    
    try:
        instances = ec2.describe_instances(
            Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
        )
        
        rightsizing_opportunities = 0
        
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_id = instance['InstanceId']
                instance_type = instance['InstanceType']
                
                # Get CPU utilization for last 7 days
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(days=7)
                
                cpu_metrics = cloudwatch.get_metric_statistics(
                    Namespace='AWS/EC2',
                    MetricName='CPUUtilization',
                    Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=3600,
                    Statistics=['Average']
                )
                
                if cpu_metrics['Datapoints']:
                    avg_cpu = sum(dp['Average'] for dp in cpu_metrics['Datapoints']) / len(cpu_metrics['Datapoints'])
                    
                    if avg_cpu < 20:  # Low utilization threshold
                        rightsizing_opportunities += 1
                        logger.info(f"Instance {instance_id} ({instance_type}) has low CPU: {avg_cpu:.1f}%")
        
        # Send metrics
        cloudwatch.put_metric_data(
            Namespace='CostOptimization',
            MetricData=[{
                'MetricName': 'InstancesRightsized',
                'Value': rightsizing_opportunities,
                'Unit': 'Count'
            }]
        )
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'rightsizing_opportunities': rightsizing_opportunities
            })
        }
        
    except Exception as e:
        logger.error(f"Error in EC2 rightsizing: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
```

### 2.3 Spot Instance Optimizer
Create `lambda-functions/spot_optimizer.py`:

```python
import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """Analyze Spot instance opportunities"""
    
    ec2 = boto3.client('ec2')
    
    try:
        # Get current On-Demand instances
        instances = ec2.describe_instances(
            Filters=[
                {'Name': 'instance-state-name', 'Values': ['running']},
                {'Name': 'instance-lifecycle', 'Values': ['normal']}  # On-Demand instances
            ]
        )
        
        spot_opportunities = 0
        potential_savings = 0
        
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                instance_type = instance['InstanceType']
                
                # Get Spot price history
                spot_prices = ec2.describe_spot_price_history(
                    InstanceTypes=[instance_type],
                    ProductDescriptions=['Linux/UNIX'],
                    MaxResults=1
                )
                
                if spot_prices['SpotPriceHistory']:
                    spot_price = float(spot_prices['SpotPriceHistory'][0]['SpotPrice'])
                    
                    # Estimate On-Demand price (simplified)
                    od_price_map = {
                        't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416,
                        't3.large': 0.0832, 'm5.large': 0.096, 'm5.xlarge': 0.192
                    }
                    
                    od_price = od_price_map.get(instance_type, 0.1)  # Default fallback
                    
                    if spot_price < od_price * 0.7:  # 30%+ savings threshold
                        spot_opportunities += 1
                        hourly_savings = od_price - spot_price
                        monthly_savings = hourly_savings * 24 * 30
                        potential_savings += monthly_savings
                        
                        logger.info(f"Spot opportunity: {instance_type}, save ${monthly_savings:.2f}/month")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'spot_opportunities': spot_opportunities,
                'potential_monthly_savings': round(potential_savings, 2)
            })
        }
        
    except Exception as e:
        logger.error(f"Error in spot optimization: {str(e)}")
        return {'statusCode': 500, 'body': json.dumps({'error': str(e)})}
```

## Step 3: Terraform Infrastructure

### 3.1 IAM Module
Create `terraform/modules/iam/main.tf`:

```hcl
resource "aws_iam_role" "lambda_execution_role" {
  name = "${var.environment}-finops-lambda-role"

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

  tags = var.tags
}

resource "aws_iam_role_policy" "cost_optimization_policy" {
  name = "${var.environment}-cost-optimization-policy"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeVolumes",
          "ec2:DescribeSnapshots",
          "ec2:DescribeSpotPriceHistory",
          "cloudwatch:PutMetricData",
          "cloudwatch:GetMetricStatistics",
          "ce:GetCostAndUsage",
          "ce:GetUsageReport"
        ]
        Resource = "*"
      }
    ]
  })
}
```

Create `terraform/modules/iam/variables.tf`:

```hcl
variable "environment" {
  description = "Environment name"
  type        = string
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
```

Create `terraform/modules/iam/outputs.tf`:

```hcl
output "lambda_role_arn" {
  description = "ARN of the Lambda execution role"
  value       = aws_iam_role.lambda_execution_role.arn
}

output "lambda_role_name" {
  description = "Name of the Lambda execution role"
  value       = aws_iam_role.lambda_execution_role.name
}
```

### 3.2 Lambda Module
Create `terraform/modules/lambda/main.tf`:

```hcl
locals {
  lambda_functions = {
    "cost-optimizer" = {
      filename = "cost_optimizer.py"
      handler  = "cost_optimizer.lambda_handler"
      timeout  = 300
      memory   = 256
      schedule = "rate(6 hours)"
    }
    "ec2-rightsizing" = {
      filename = "ec2_rightsizing.py"
      handler  = "ec2_rightsizing.lambda_handler"
      timeout  = 600
      memory   = 512
      schedule = "rate(12 hours)"
    }
    "spot-optimizer" = {
      filename = "spot_optimizer.py"
      handler  = "spot_optimizer.lambda_handler"
      timeout  = 300
      memory   = 512
      schedule = "rate(6 hours)"
    }
  }
}

# Create ZIP files for Lambda functions
data "archive_file" "lambda_zip" {
  for_each = local.lambda_functions
  
  type        = "zip"
  source_file = "${path.root}/../../lambda-functions/${each.value.filename}"
  output_path = "${each.key}.zip"
}

# Lambda functions
resource "aws_lambda_function" "cost_optimizer" {
  for_each = local.lambda_functions

  filename         = data.archive_file.lambda_zip[each.key].output_path
  function_name    = "${var.environment}-${each.key}"
  role            = var.lambda_role_arn
  handler         = each.value.handler
  source_code_hash = data.archive_file.lambda_zip[each.key].output_base64sha256
  runtime         = "python3.9"
  timeout         = each.value.timeout
  memory_size     = each.value.memory

  environment {
    variables = {
      ENVIRONMENT = var.environment
      LOG_LEVEL   = var.log_level
    }
  }

  tags = merge(var.tags, {
    Name     = "${var.environment}-${each.key}"
    Function = each.key
  })
}

# EventBridge rules for scheduling
resource "aws_cloudwatch_event_rule" "lambda_schedule" {
  for_each = local.lambda_functions

  name                = "${var.environment}-${each.key}-schedule"
  description         = "Schedule for ${each.key}"
  schedule_expression = each.value.schedule

  tags = var.tags
}

# EventBridge targets
resource "aws_cloudwatch_event_target" "lambda_target" {
  for_each = local.lambda_functions

  rule      = aws_cloudwatch_event_rule.lambda_schedule[each.key].name
  target_id = "${each.key}Target"
  arn       = aws_lambda_function.cost_optimizer[each.key].arn
}

# Lambda permissions for EventBridge
resource "aws_lambda_permission" "allow_cloudwatch" {
  for_each = local.lambda_functions

  statement_id  = "AllowExecutionFromCloudWatch-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.cost_optimizer[each.key].function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.lambda_schedule[each.key].arn
}
```

### 3.3 Monitoring Module
Create `terraform/modules/monitoring/main.tf`:

```hcl
# SNS Topic for alerts
resource "aws_sns_topic" "cost_alerts" {
  name = "${var.environment}-finops-alerts"
  tags = var.tags
}

# SNS Subscription
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = length(var.alert_emails)
  topic_arn = aws_sns_topic.cost_alerts.arn
  protocol  = "email"
  endpoint  = var.alert_emails[count.index]
}

# CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "finops_dashboard" {
  dashboard_name = "${var.environment}-finops-platform"

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
            ["CostOptimization", "EstimatedMonthlySavings"],
            [".", "VolumesOptimized"],
            [".", "SnapshotsDeleted"],
            [".", "InstancesRightsized"]
          ]
          period = 86400
          stat   = "Sum"
          region = var.aws_region
          title  = "Cost Optimization Metrics"
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
            ["AWS/Lambda", "Duration", "FunctionName", "${var.environment}-cost-optimizer"],
            [".", "Errors", ".", "."],
            [".", "Invocations", ".", "."]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Lambda Performance"
        }
      }
    ]
  })
}

# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "high_cost_alarm" {
  alarm_name          = "${var.environment}-high-cost-detected"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "EstimatedCharges"
  namespace           = "AWS/Billing"
  period              = "86400"
  statistic           = "Maximum"
  threshold           = "1000"
  alarm_description   = "This metric monitors AWS estimated charges"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    Currency = "USD"
  }

  tags = var.tags
}

# Lambda Error Alarms
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each = var.lambda_functions

  alarm_name          = "${var.environment}-${each.key}-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Lambda function ${each.key} error rate too high"
  alarm_actions       = [aws_sns_topic.cost_alerts.arn]

  dimensions = {
    FunctionName = "${var.environment}-${each.key}"
  }

  tags = var.tags
}
```

### 3.4 Environment Configuration
Create `terraform/environments/dev/main.tf`:

```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

locals {
  environment = "dev"
  
  common_tags = {
    Environment = "development"
    Project     = "finops-platform"
    ManagedBy   = "terraform"
    Owner       = "dev-team"
  }

  lambda_functions = {
    "cost-optimizer"           = {}
    "ec2-rightsizing"         = {}
    "spot-optimizer"          = {}
  }
}

# IAM Module
module "iam" {
  source = "../../modules/iam"
  
  environment = local.environment
  tags        = local.common_tags
}

# Lambda Module
module "lambda" {
  source = "../../modules/lambda"
  
  environment      = local.environment
  lambda_role_arn  = module.iam.lambda_role_arn
  log_level        = "DEBUG"
  tags             = local.common_tags
}

# Monitoring Module
module "monitoring" {
  source = "../../modules/monitoring"
  
  environment       = local.environment
  aws_region        = var.aws_region
  alert_emails      = var.alert_emails
  lambda_functions  = local.lambda_functions
  tags              = local.common_tags
}
```

Create `terraform/environments/dev/variables.tf`:

```hcl
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "alert_emails" {
  description = "Email addresses for cost alerts"
  type        = list(string)
  default     = ["finops-alerts@example.com"]
}
```

## Step 4: Deployment Scripts

Create `scripts/deploy.sh`:

```bash
#!/bin/bash

set -e

ENVIRONMENT=${1:-dev}
AWS_REGION=${2:-us-east-1}

echo "Deploying FinOps Platform to $ENVIRONMENT environment in $AWS_REGION"

# Navigate to environment directory
cd terraform/environments/$ENVIRONMENT

# Initialize Terraform
terraform init

# Plan deployment
terraform plan -var="aws_region=$AWS_REGION"

# Apply (with confirmation)
read -p "Do you want to apply these changes? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    terraform apply -var="aws_region=$AWS_REGION" -auto-approve
    echo "Deployment completed successfully!"
else
    echo "Deployment cancelled."
fi
```

Create `scripts/test-functions.sh`:

```bash
#!/bin/bash

ENVIRONMENT=${1:-dev}
AWS_REGION=${2:-us-east-1}

echo "Testing Lambda functions in $ENVIRONMENT environment"

FUNCTIONS=("cost-optimizer" "ec2-rightsizing" "spot-optimizer")

for func in "${FUNCTIONS[@]}"; do
    echo "Testing $ENVIRONMENT-$func..."
    aws lambda invoke \
        --function-name "$ENVIRONMENT-$func" \
        --region "$AWS_REGION" \
        --payload '{}' \
        response.json
    
    echo "Response:"
    cat response.json
    echo -e "\n---\n"
done

rm -f response.json
```

## Step 5: Manual Deployment Steps

1. **Setup Project Structure:**
```bash
mkdir aws-finops-platform && cd aws-finops-platform
# Copy all files from above into appropriate directories
```

2. **Configure AWS CLI:**
```bash
aws configure
# Enter your AWS credentials and region
```

3. **Deploy Infrastructure:**
```bash
chmod +x scripts/deploy.sh
./scripts/deploy.sh dev us-east-1
```

4. **Test Functions:**
```bash
chmod +x scripts/test-functions.sh
./scripts/test-functions.sh dev us-east-1
```

5. **Monitor Dashboard:**
- Go to CloudWatch Console
- Navigate to Dashboards
- Open "dev-finops-platform" dashboard

6. **Verify Alerts:**
- Check SNS topic subscriptions
- Confirm email subscription

## Step 6: Cleanup

Create `scripts/destroy.sh`:

```bash
#!/bin/bash

ENVIRONMENT=${1:-dev}

echo "Destroying FinOps Platform in $ENVIRONMENT environment"

cd terraform/environments/$ENVIRONMENT

read -p "Are you sure you want to destroy all resources? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    terraform destroy -auto-approve
    echo "Resources destroyed successfully!"
else
    echo "Destruction cancelled."
fi
```

## Cost Estimation

**Monthly AWS Costs (Dev Environment):**
- Lambda: ~$5-10 (based on execution frequency)
- CloudWatch: ~$2-5 (metrics and alarms)
- SNS: ~$1 (notifications)
- **Total: ~$8-16/month**

**Potential Savings:**
- Unattached EBS volumes: $50-200/month
- EC2 right-sizing: $100-500/month  
- Spot instances: $200-1000/month
- **Total Potential: $350-1700/month**

**ROI: 2000-10000%** (savings vs platform cost)
