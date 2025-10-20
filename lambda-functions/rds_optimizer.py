import boto3
import json
from datetime import datetime, timedelta

def lambda_handler(event, context):
    rds = boto3.client('rds')
    cloudwatch = boto3.client('cloudwatch')
    
    results = {
        'idle_databases': [],
        'oversized_databases': [],
        'potential_savings': 0
    }
    
    # Get all RDS instances
    db_instances = rds.describe_db_instances()
    
    for db in db_instances['DBInstances']:
        db_id = db['DBInstanceIdentifier']
        db_class = db['DBInstanceClass']
        
        # Check CPU utilization
        cpu_metrics = cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='CPUUtilization',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
            StartTime=datetime.utcnow() - timedelta(days=7),
            EndTime=datetime.utcnow(),
            Period=3600,
            Statistics=['Average']
        )
        
        # Check database connections
        connection_metrics = cloudwatch.get_metric_statistics(
            Namespace='AWS/RDS',
            MetricName='DatabaseConnections',
            Dimensions=[{'Name': 'DBInstanceIdentifier', 'Value': db_id}],
            StartTime=datetime.utcnow() - timedelta(days=7),
            EndTime=datetime.utcnow(),
            Period=3600,
            Statistics=['Average']
        )
        
        if cpu_metrics['Datapoints'] and connection_metrics['Datapoints']:
            avg_cpu = sum(dp['Average'] for dp in cpu_metrics['Datapoints']) / len(cpu_metrics['Datapoints'])
            avg_connections = sum(dp['Average'] for dp in connection_metrics['Datapoints']) / len(connection_metrics['Datapoints'])
            
            # Identify idle databases
            if avg_cpu < 5 and avg_connections < 1:
                monthly_cost = get_rds_cost(db_class) * 24 * 30
                results['idle_databases'].append({
                    'db_identifier': db_id,
                    'db_class': db_class,
                    'avg_cpu': round(avg_cpu, 2),
                    'avg_connections': round(avg_connections, 2),
                    'monthly_cost': round(monthly_cost, 2),
                    'recommendation': 'Consider stopping or downsizing'
                })
                results['potential_savings'] += monthly_cost * 0.8  # 80% savings if stopped
            
            # Identify oversized databases
            elif avg_cpu < 20 and avg_connections < 10:
                smaller_class = get_smaller_db_class(db_class)
                if smaller_class:
                    current_cost = get_rds_cost(db_class) * 24 * 30
                    new_cost = get_rds_cost(smaller_class) * 24 * 30
                    monthly_savings = current_cost - new_cost
                    
                    results['oversized_databases'].append({
                        'db_identifier': db_id,
                        'current_class': db_class,
                        'recommended_class': smaller_class,
                        'avg_cpu': round(avg_cpu, 2),
                        'monthly_savings': round(monthly_savings, 2)
                    })
                    results['potential_savings'] += monthly_savings
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def get_rds_cost(db_class):
    # Simplified RDS pricing (USD per hour)
    pricing = {
        'db.t3.micro': 0.017,
        'db.t3.small': 0.034,
        'db.t3.medium': 0.068,
        'db.t3.large': 0.136,
        'db.m5.large': 0.192,
        'db.m5.xlarge': 0.384
    }
    return pricing.get(db_class, 0.1)

def get_smaller_db_class(current_class):
    downsize_map = {
        'db.t3.large': 'db.t3.medium',
        'db.t3.medium': 'db.t3.small',
        'db.m5.xlarge': 'db.m5.large',
        'db.m5.large': 'db.t3.large'
    }
    return downsize_map.get(current_class)
