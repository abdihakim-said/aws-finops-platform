# Contributing to AWS FinOps Platform

## Welcome Contributors! 🎉

Thank you for your interest in contributing to the AWS FinOps Platform. This document provides guidelines and information for contributors.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)
- [Architecture Guidelines](#architecture-guidelines)

## Code of Conduct

This project adheres to professional standards:
- Be respectful and inclusive
- Focus on constructive feedback
- Prioritize security and cost optimization best practices
- Maintain enterprise-grade code quality

## Getting Started

### Prerequisites

- Python 3.9+
- AWS CLI configured
- Terraform 1.5+
- Docker (for local development)

### Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd aws-finops-platform

# Setup development environment
make install-dev

# Run initial validation
make validate
```

## Development Workflow

### 1. Branch Strategy

```bash
# Create feature branch
git checkout -b feature/cost-optimizer-enhancement

# Create bugfix branch
git checkout -b bugfix/lambda-timeout-issue

# Create documentation branch
git checkout -b docs/api-documentation
```

### 2. Development Process

```bash
# Make your changes
# ...

# Run code quality checks
make lint

# Run tests
make test

# Validate infrastructure
make plan
```

### 3. Commit Standards

Use conventional commits:

```bash
# Feature commits
git commit -m "feat(lambda): add S3 intelligent tiering optimizer"

# Bug fixes
git commit -m "fix(ec2): resolve rightsizing calculation error"

# Documentation
git commit -m "docs(api): add Lambda function API documentation"

# Infrastructure
git commit -m "infra(terraform): add multi-region support"
```

## Code Standards

### Python Code Quality

```python
# Use type hints
def calculate_savings(volume_size: int, volume_type: str) -> float:
    """Calculate potential savings from volume optimization."""
    pass

# Use docstrings
def optimize_ebs_volumes(ec2_client: boto3.client) -> Dict[str, Any]:
    """
    Optimize EBS volumes by converting gp2 to gp3.
    
    Args:
        ec2_client: Boto3 EC2 client instance
        
    Returns:
        Dictionary containing optimization results
        
    Raises:
        OptimizationError: If volume optimization fails
    """
    pass

# Use proper error handling
try:
    result = ec2_client.modify_volume(VolumeId=volume_id, VolumeType='gp3')
except ClientError as e:
    logger.error(f"Failed to optimize volume {volume_id}: {e}")
    raise OptimizationError(f"Volume optimization failed: {e}")
```

### Lambda Function Structure

```python
# Standard Lambda structure
import json
import logging
from typing import Dict, Any
from src.shared.aws_clients import get_ec2_client
from src.shared.metrics import publish_metrics
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda function entry point.
    
    Args:
        event: Lambda event data
        context: Lambda context object
        
    Returns:
        Response dictionary with status and results
    """
    try:
        # Implementation
        return {
            'statusCode': 200,
            'body': json.dumps(results)
        }
    except Exception as e:
        logger.error(f"Lambda execution failed: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
```

## Testing Requirements

### Unit Tests (Required)

```python
# tests/unit/lambda/test_cost_optimizer.py
import pytest
from moto import mock_ec2
from src.lambda.cost_optimization.cost_optimizer import lambda_handler

@mock_ec2
def test_cost_optimizer_success():
    """Test successful cost optimization."""
    # Setup
    event = {'account_id': '123456789012'}
    
    # Execute
    result = lambda_handler(event, None)
    
    # Assert
    assert result['statusCode'] == 200
    assert 'volumes_optimized' in json.loads(result['body'])
```

### Integration Tests (Recommended)

```python
# tests/integration/test_aws_integration.py
import boto3
import pytest
from src.lambda.cost_optimization.cost_optimizer import lambda_handler

@pytest.mark.integration
def test_real_aws_integration():
    """Test with real AWS services (requires AWS credentials)."""
    # Implementation for integration testing
    pass
```

### Test Coverage Requirements

- **Minimum Coverage**: 80%
- **Lambda Functions**: 90% coverage required
- **Shared Libraries**: 85% coverage required
- **Critical Paths**: 100% coverage required

```bash
# Run coverage analysis
make test-coverage
```

## Pull Request Process

### 1. Pre-PR Checklist

- [ ] Code follows style guidelines
- [ ] Tests pass locally (`make test`)
- [ ] Code coverage meets requirements
- [ ] Documentation updated
- [ ] Security scan passes (`make security-scan`)
- [ ] Infrastructure validates (`make plan`)

### 2. PR Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] Infrastructure change

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing completed

## Cost Impact
- Estimated monthly savings: £X,XXX
- Resource impact: [describe]
- Performance impact: [describe]

## Security Considerations
- [ ] No sensitive data exposed
- [ ] IAM permissions follow least privilege
- [ ] Security scan passed

## Checklist
- [ ] Code follows project standards
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
```

### 3. Review Process

1. **Automated Checks**: CI/CD pipeline runs automatically
2. **Code Review**: Minimum 2 approvals required
3. **Security Review**: Required for infrastructure changes
4. **Performance Review**: Required for Lambda changes

## Architecture Guidelines

### Lambda Function Design

```python
# Good: Single responsibility
def optimize_ebs_volumes():
    """Focuses only on EBS volume optimization."""
    pass

# Good: Proper error handling
def safe_volume_modification(volume_id: str) -> bool:
    """Safely modify volume with proper error handling."""
    try:
        # Implementation
        return True
    except Exception as e:
        logger.error(f"Volume modification failed: {e}")
        return False

# Good: Metrics and monitoring
def publish_optimization_metrics(results: Dict[str, Any]) -> None:
    """Publish metrics to CloudWatch."""
    cloudwatch.put_metric_data(
        Namespace='FinOps/Optimization',
        MetricData=[
            {
                'MetricName': 'VolumesOptimized',
                'Value': results['volumes_optimized'],
                'Unit': 'Count'
            }
        ]
    )
```

### Infrastructure Guidelines

```hcl
# Terraform best practices
resource "aws_lambda_function" "cost_optimizer" {
  function_name = "${var.environment}-cost-optimizer"
  
  # Use consistent naming
  tags = {
    Environment = var.environment
    Project     = "finops-platform"
    Owner       = "platform-team"
    CostCenter  = "engineering"
  }
  
  # Security best practices
  kms_key_arn = aws_kms_key.lambda_encryption.arn
  
  # Monitoring
  depends_on = [aws_cloudwatch_log_group.lambda_logs]
}
```

## Security Guidelines

### 1. IAM Policies

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ec2:DescribeVolumes",
        "ec2:ModifyVolume"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestedRegion": ["us-east-1", "us-west-2"]
        }
      }
    }
  ]
}
```

### 2. Secrets Management

```python
# Good: Use AWS Secrets Manager
import boto3

def get_api_key() -> str:
    """Retrieve API key from Secrets Manager."""
    secrets_client = boto3.client('secretsmanager')
    response = secrets_client.get_secret_value(SecretId='finops/api-key')
    return response['SecretString']

# Bad: Hardcoded secrets
API_KEY = "hardcoded-secret"  # Never do this
```

## Performance Guidelines

### Lambda Optimization

```python
# Good: Reuse connections
import boto3

# Initialize outside handler for connection reuse
ec2_client = boto3.client('ec2')

def lambda_handler(event, context):
    # Use pre-initialized client
    volumes = ec2_client.describe_volumes()
```

### Cost Optimization

```python
# Good: Batch operations
def batch_volume_modifications(volume_ids: List[str]) -> None:
    """Process volumes in batches for efficiency."""
    batch_size = 10
    for i in range(0, len(volume_ids), batch_size):
        batch = volume_ids[i:i + batch_size]
        process_volume_batch(batch)
```

## Documentation Standards

### Code Documentation

```python
def calculate_ri_savings(instance_type: str, usage_hours: int) -> float:
    """
    Calculate Reserved Instance savings potential.
    
    This function analyzes instance usage patterns and calculates
    the potential cost savings from purchasing Reserved Instances.
    
    Args:
        instance_type: EC2 instance type (e.g., 'm5.large')
        usage_hours: Monthly usage hours for the instance type
        
    Returns:
        Monthly savings amount in USD
        
    Example:
        >>> calculate_ri_savings('m5.large', 720)
        245.50
        
    Note:
        Calculation assumes 1-year term, no upfront payment.
    """
    pass
```

### API Documentation

Use OpenAPI/Swagger for Lambda APIs:

```yaml
# docs/api/lambda_apis.yaml
openapi: 3.0.0
info:
  title: FinOps Platform Lambda APIs
  version: 1.0.0
paths:
  /optimize/ebs:
    post:
      summary: Optimize EBS volumes
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              properties:
                account_id:
                  type: string
                region:
                  type: string
```

## Getting Help

- **Documentation**: Check `docs/` directory
- **Issues**: Create GitHub issue with detailed description
- **Discussions**: Use GitHub Discussions for questions
- **Security**: Email security@company.com for security issues

## Recognition

Contributors will be recognized in:
- CHANGELOG.md for significant contributions
- README.md contributors section
- Annual platform awards for major improvements

Thank you for contributing to the AWS FinOps Platform! 🚀
