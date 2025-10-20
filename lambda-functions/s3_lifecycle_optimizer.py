import boto3
import json
from datetime import datetime, timedelta

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    
    results = {
        'buckets_optimized': 0,
        'lifecycle_policies_created': 0,
        'estimated_savings': 0
    }
    
    # Get all S3 buckets
    buckets = s3.list_buckets()
    
    for bucket in buckets['Buckets']:
        bucket_name = bucket['Name']
        
        try:
            # Check if lifecycle policy exists
            try:
                s3.get_bucket_lifecycle_configuration(Bucket=bucket_name)
                continue  # Policy already exists
            except s3.exceptions.ClientError:
                pass  # No policy exists, create one
            
            # Get bucket size and analyze objects
            total_size = 0
            old_objects = 0
            
            paginator = s3.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=bucket_name):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        total_size += obj['Size']
                        # Check if object is older than 30 days
                        if obj['LastModified'] < datetime.now(obj['LastModified'].tzinfo) - timedelta(days=30):
                            old_objects += 1
            
            # Create lifecycle policy if bucket has old objects
            if old_objects > 0 and total_size > 1024*1024*100:  # > 100MB
                lifecycle_policy = {
                    'Rules': [
                        {
                            'ID': 'CostOptimizationRule',
                            'Status': 'Enabled',
                            'Transitions': [
                                {
                                    'Days': 30,
                                    'StorageClass': 'STANDARD_IA'
                                },
                                {
                                    'Days': 90,
                                    'StorageClass': 'GLACIER'
                                },
                                {
                                    'Days': 365,
                                    'StorageClass': 'DEEP_ARCHIVE'
                                }
                            ]
                        }
                    ]
                }
                
                s3.put_bucket_lifecycle_configuration(
                    Bucket=bucket_name,
                    LifecycleConfiguration=lifecycle_policy
                )
                
                # Calculate estimated savings
                gb_size = total_size / (1024**3)
                monthly_savings = gb_size * 0.015  # Estimated 60% savings on old data
                
                results['buckets_optimized'] += 1
                results['lifecycle_policies_created'] += 1
                results['estimated_savings'] += monthly_savings
                
                print(f"Created lifecycle policy for {bucket_name}: ${monthly_savings:.2f}/month savings")
                
        except Exception as e:
            print(f"Error processing bucket {bucket_name}: {str(e)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
