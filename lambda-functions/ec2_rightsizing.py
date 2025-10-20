import boto3
import json
from datetime import datetime, timedelta

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')
    
    results = {
        'underutilized_instances': [],
        'potential_savings': 0,
        'recommendations': []
    }
    
    # Get all running instances
    instances = ec2.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_id = instance['InstanceId']
            instance_type = instance['InstanceType']
            
            # Get CPU utilization for last 7 days
            cpu_metrics = cloudwatch.get_metric_statistics(
                Namespace='AWS/EC2',
                MetricName='CPUUtilization',
                Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
                StartTime=datetime.utcnow() - timedelta(days=7),
                EndTime=datetime.utcnow(),
                Period=3600,
                Statistics=['Average']
            )
            
            if cpu_metrics['Datapoints']:
                avg_cpu = sum(dp['Average'] for dp in cpu_metrics['Datapoints']) / len(cpu_metrics['Datapoints'])
                
                # Recommend downsizing if CPU < 20%
                if avg_cpu < 20:
                    recommendation = get_smaller_instance_type(instance_type)
                    if recommendation:
                        current_cost = get_instance_cost(instance_type)
                        new_cost = get_instance_cost(recommendation)
                        monthly_savings = (current_cost - new_cost) * 24 * 30
                        
                        results['underutilized_instances'].append({
                            'instance_id': instance_id,
                            'current_type': instance_type,
                            'recommended_type': recommendation,
                            'avg_cpu': round(avg_cpu, 2),
                            'monthly_savings': round(monthly_savings, 2)
                        })
                        
                        results['potential_savings'] += monthly_savings
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def get_smaller_instance_type(current_type):
    # Simplified downsizing logic
    downsize_map = {
        'm5.large': 'm5.medium',
        'm5.xlarge': 'm5.large',
        't3.large': 't3.medium',
        't3.xlarge': 't3.large'
    }
    return downsize_map.get(current_type)

def get_instance_cost(instance_type):
    # Simplified pricing (USD per hour)
    pricing = {
        'm5.medium': 0.096,
        'm5.large': 0.192,
        'm5.xlarge': 0.384,
        't3.medium': 0.0416,
        't3.large': 0.0832,
        't3.xlarge': 0.1664
    }
    return pricing.get(instance_type, 0.1)
