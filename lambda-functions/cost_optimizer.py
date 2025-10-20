import boto3
import json
from datetime import datetime, timedelta

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    cloudwatch = boto3.client('cloudwatch')
    
    results = {
        'volumes_optimized': 0,
        'snapshots_deleted': 0,
        'estimated_savings': 0
    }
    
    # Optimize EBS volumes (gp2 to gp3)
    volumes = ec2.describe_volumes(
        Filters=[{'Name': 'volume-type', 'Values': ['gp2']}]
    )
    
    for volume in volumes['Volumes']:
        volume_id = volume['VolumeId']
        size = volume['Size']
        
        try:
            ec2.modify_volume(
                VolumeId=volume_id,
                VolumeType='gp3'
            )
            
            # Calculate savings (20% cost reduction)
            monthly_savings = size * 0.08 * 0.20  # $0.08/GB/month * 20% savings
            results['estimated_savings'] += monthly_savings
            results['volumes_optimized'] += 1
            
            print(f"Optimized volume {volume_id}: ${monthly_savings:.2f}/month savings")
            
        except Exception as e:
            print(f"Failed to optimize volume {volume_id}: {str(e)}")
    
    # Clean up stale snapshots
    snapshots = ec2.describe_snapshots(OwnerIds=['self'])
    cutoff_date = datetime.now() - timedelta(days=30)
    
    for snapshot in snapshots['Snapshots']:
        snapshot_date = snapshot['StartTime'].replace(tzinfo=None)
        
        if snapshot_date < cutoff_date:
            try:
                # Check if snapshot is still needed
                volume_id = snapshot.get('VolumeId')
                if volume_id:
                    try:
                        ec2.describe_volumes(VolumeIds=[volume_id])
                        continue  # Volume exists, keep snapshot
                    except:
                        pass  # Volume doesn't exist, can delete snapshot
                
                ec2.delete_snapshot(SnapshotId=snapshot['SnapshotId'])
                results['snapshots_deleted'] += 1
                
                # Estimate storage savings
                if 'VolumeSize' in snapshot:
                    storage_savings = snapshot['VolumeSize'] * 0.05  # $0.05/GB/month
                    results['estimated_savings'] += storage_savings
                
            except Exception as e:
                print(f"Failed to delete snapshot {snapshot['SnapshotId']}: {str(e)}")
    
    # Send metrics to CloudWatch
    cloudwatch.put_metric_data(
        Namespace='CostOptimization',
        MetricData=[
            {
                'MetricName': 'VolumesOptimized',
                'Value': results['volumes_optimized'],
                'Unit': 'Count'
            },
            {
                'MetricName': 'SnapshotsDeleted',
                'Value': results['snapshots_deleted'],
                'Unit': 'Count'
            },
            {
                'MetricName': 'EstimatedMonthlySavings',
                'Value': results['estimated_savings'],
                'Unit': 'None'
            }
        ]
    )
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
