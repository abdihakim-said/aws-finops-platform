#!/bin/bash

# Enterprise deployment script for modular Terraform

ENVIRONMENT=${1:-dev}
ACTION=${2:-plan}

if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|prod)$ ]]; then
    echo "❌ Invalid environment. Use: dev, staging, or prod"
    exit 1
fi

if [[ ! "$ACTION" =~ ^(plan|apply|destroy)$ ]]; then
    echo "❌ Invalid action. Use: plan, apply, or destroy"
    exit 1
fi

echo "🚀 Deploying FinOps Platform to $ENVIRONMENT environment..."

# Package Lambda functions
echo "📦 Packaging Lambda functions..."
cd lambda-functions
for func in *.py; do
    if [[ "$func" != "__init__.py" ]]; then
        func_name="${func%.py}"
        zip -q "${func_name}.zip" "$func"
        echo "  ✓ Packaged $func_name"
    fi
done

# Move packages to environment directory
mv *.zip "../terraform/environments/$ENVIRONMENT/"
cd ..

# Deploy infrastructure
echo "🏗️  Deploying infrastructure..."
cd "terraform/environments/$ENVIRONMENT"

# Initialize Terraform
terraform init

# Validate configuration
terraform validate
if [ $? -ne 0 ]; then
    echo "❌ Terraform validation failed"
    exit 1
fi

# Execute action
case $ACTION in
    plan)
        terraform plan -var-file="terraform.tfvars"
        ;;
    apply)
        terraform apply -var-file="terraform.tfvars" -auto-approve
        echo "✅ Deployment complete!"
        echo "📊 View dashboard: https://console.aws.amazon.com/cloudwatch/home#dashboards:name=${ENVIRONMENT}-finops-platform"
        ;;
    destroy)
        terraform destroy -var-file="terraform.tfvars" -auto-approve
        echo "🗑️  Environment destroyed"
        ;;
esac
