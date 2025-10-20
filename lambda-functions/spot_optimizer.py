import boto3
import json

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    autoscaling = boto3.client('autoscaling')
    
    results = {
        'spot_opportunities': [],
        'asg_recommendations': [],
        'potential_savings': 0
    }
    
    # Analyze current On-Demand instances for Spot conversion
    instances = ec2.describe_instances(
        Filters=[
            {'Name': 'instance-state-name', 'Values': ['running']},
            {'Name': 'instance-lifecycle', 'Values': ['normal']}  # On-Demand only
        ]
    )
    
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            instance_type = instance['InstanceType']
            az = instance['Placement']['AvailabilityZone']
            
            # Check if workload is suitable for Spot (non-critical tags)
            tags = {tag['Key']: tag['Value'] for tag in instance.get('Tags', [])}
            environment = tags.get('Environment', '').lower()
            workload_type = tags.get('WorkloadType', '').lower()
            
            # Suitable for Spot: dev, test, batch, analytics
            if any(keyword in environment for keyword in ['dev', 'test', 'staging']) or \
               any(keyword in workload_type for keyword in ['batch', 'analytics', 'processing']):
                
                # Get current Spot pricing
                spot_prices = ec2.describe_spot_price_history(
                    InstanceTypes=[instance_type],
                    ProductDescriptions=['Linux/UNIX'],
                    AvailabilityZone=az,
                    MaxResults=1
                )
                
                if spot_prices['SpotPriceHistory']:
                    spot_price = float(spot_prices['SpotPriceHistory'][0]['SpotPrice'])
                    on_demand_price = get_on_demand_price(instance_type)
                    
                    if spot_price < on_demand_price * 0.7:  # >30% savings
                        monthly_savings = (on_demand_price - spot_price) * 24 * 30
                        
                        results['spot_opportunities'].append({
                            'instance_id': instance['InstanceId'],
                            'instance_type': instance_type,
                            'current_price': f"${on_demand_price:.4f}/hour",
                            'spot_price': f"${spot_price:.4f}/hour",
                            'savings_percentage': f"{((on_demand_price - spot_price) / on_demand_price * 100):.1f}%",
                            'monthly_savings': f"${monthly_savings:.2f}",
                            'environment': environment,
                            'recommendation': 'Convert to Spot Instance'
                        })
                        
                        results['potential_savings'] += monthly_savings
    
    # Analyze Auto Scaling Groups for mixed instance types
    asgs = autoscaling.describe_auto_scaling_groups()
    
    for asg in asgs['AutoScalingGroups']:
        asg_name = asg['AutoScalingGroupName']
        
        # Check if ASG uses only On-Demand instances
        if not asg.get('MixedInstancesPolicy'):
            launch_template = asg.get('LaunchTemplate') or asg.get('LaunchConfigurationName')
            
            if launch_template:
                # Recommend mixed instance policy
                results['asg_recommendations'].append({
                    'asg_name': asg_name,
                    'current_capacity': asg['DesiredCapacity'],
                    'recommendation': 'Implement Mixed Instance Policy',
                    'suggested_spot_percentage': '70%',
                    'estimated_savings': '50-70%',
                    'diversification': 'Use 3+ instance types across AZs'
                })
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def get_on_demand_price(instance_type):
    # Simplified On-Demand pricing
    pricing = {
        't3.micro': 0.0104, 't3.small': 0.0208, 't3.medium': 0.0416,
        't3.large': 0.0832, 'm5.large': 0.096, 'm5.xlarge': 0.192,
        'c5.large': 0.085, 'c5.xlarge': 0.17
    }
    return pricing.get(instance_type, 0.1)
