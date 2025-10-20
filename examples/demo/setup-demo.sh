#!/bin/bash

echo "🚀 Setting up FinOps Platform Demo Environment..."

# Create demo resources for optimization
aws ec2 create-volume --size 10 --volume-type gp2 --availability-zone us-east-1a --tag-specifications 'ResourceType=volume,Tags=[{Key=Environment,Value=demo},{Key=Purpose,Value=cost-optimization-demo}]'

# Create test snapshot
VOLUME_ID=$(aws ec2 describe-volumes --filters "Name=tag:Purpose,Values=cost-optimization-demo" --query 'Volumes[0].VolumeId' --output text)
aws ec2 create-snapshot --volume-id $VOLUME_ID --description "Demo snapshot for cleanup"

# Launch test instance for right-sizing demo
aws ec2 run-instances --image-id ami-0abcdef1234567890 --instance-type t3.large --tag-specifications 'ResourceType=instance,Tags=[{Key=Environment,Value=demo},{Key=WorkloadType,Value=batch}]'

echo "✅ Demo environment created!"
echo "💡 Run the optimization functions to see cost savings in action"
