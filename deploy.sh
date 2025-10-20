#!/bin/bash

echo "🚀 Deploying AWS Cost Optimization Platform..."

# Package Lambda function
cd lambda-functions
zip -r ../terraform/ebs_optimizer.zip cost_optimizer.py
cd ..

# Deploy infrastructure
cd terraform
terraform init
terraform plan
terraform apply -auto-approve

echo "✅ Deployment complete!"
echo "📊 View metrics in CloudWatch dashboard: CostOptimization"
echo "💰 Estimated monthly savings will appear within 24 hours"
