import boto3
import json

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    elbv2 = boto3.client('elbv2')
    
    results = {
        'unused_security_groups': 0,
        'unused_load_balancers': 0,
        'unattached_eips': 0,
        'estimated_savings': 0
    }
    
    # Clean up unused security groups
    security_groups = ec2.describe_security_groups()
    instances = ec2.describe_instances()
    
    # Get all security groups in use
    used_sgs = set()
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            for sg in instance['SecurityGroups']:
                used_sgs.add(sg['GroupId'])
    
    for sg in security_groups['SecurityGroups']:
        if sg['GroupName'] != 'default' and sg['GroupId'] not in used_sgs:
            try:
                ec2.delete_security_group(GroupId=sg['GroupId'])
                results['unused_security_groups'] += 1
                print(f"Deleted unused security group: {sg['GroupId']}")
            except Exception as e:
                print(f"Cannot delete SG {sg['GroupId']}: {str(e)}")
    
    # Clean up unused Elastic IPs
    eips = ec2.describe_addresses()
    for eip in eips['Addresses']:
        if 'InstanceId' not in eip and 'NetworkInterfaceId' not in eip:
            try:
                ec2.release_address(AllocationId=eip['AllocationId'])
                results['unattached_eips'] += 1
                results['estimated_savings'] += 3.65  # $0.005/hour * 24 * 30
                print(f"Released unused EIP: {eip['PublicIp']}")
            except Exception as e:
                print(f"Cannot release EIP {eip['PublicIp']}: {str(e)}")
    
    # Identify unused load balancers (no targets)
    try:
        load_balancers = elbv2.describe_load_balancers()
        for lb in load_balancers['LoadBalancers']:
            lb_arn = lb['LoadBalancerArn']
            
            # Check target groups
            target_groups = elbv2.describe_target_groups(LoadBalancerArn=lb_arn)
            has_healthy_targets = False
            
            for tg in target_groups['TargetGroups']:
                targets = elbv2.describe_target_health(TargetGroupArn=tg['TargetGroupArn'])
                if any(t['TargetHealth']['State'] == 'healthy' for t in targets['TargetHealthDescriptions']):
                    has_healthy_targets = True
                    break
            
            if not has_healthy_targets:
                # Don't auto-delete, just report
                results['unused_load_balancers'] += 1
                results['estimated_savings'] += 22.5  # ~$0.025/hour * 24 * 30
                print(f"Found unused load balancer: {lb['LoadBalancerName']}")
                
    except Exception as e:
        print(f"Error checking load balancers: {str(e)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
