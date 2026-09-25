import boto3
import json
import os


def is_dry_run(event):
    # Safe by default: only act when DRY_RUN=false AND the event doesn't ask for a dry run
    if (event or {}).get('dryRun') is True:
        return True
    return os.environ.get('DRY_RUN', 'true').lower() != 'false'


def lambda_handler(event, context):
    dry_run = is_dry_run(event)
    ec2 = boto3.client('ec2')
    elbv2 = boto3.client('elbv2')
    
    results = {
        'unused_security_groups': 0,
        'unused_load_balancers': 0,
        'unattached_eips': 0,
        'estimated_savings': 0,
        'dry_run': dry_run
    }
    
    # Clean up unused security groups
    security_groups = ec2.describe_security_groups()
    
    # A security group is in use if any network interface references it
    # (covers EC2, RDS, ELB, Lambda-in-VPC, EKS, VPC endpoints, ...)
    used_sgs = set()
    for page in ec2.get_paginator('describe_network_interfaces').paginate():
        for eni in page['NetworkInterfaces']:
            for sg in eni.get('Groups', []):
                used_sgs.add(sg['GroupId'])
    # ...or is referenced by another group's rules
    for sg in security_groups['SecurityGroups']:
        for perm in sg.get('IpPermissions', []) + sg.get('IpPermissionsEgress', []):
            for pair in perm.get('UserIdGroupPairs', []):
                used_sgs.add(pair['GroupId'])
    
    for sg in security_groups['SecurityGroups']:
        if sg['GroupName'] != 'default' and sg['GroupId'] not in used_sgs:
            try:
                if not dry_run:
                    ec2.delete_security_group(GroupId=sg['GroupId'])
                results['unused_security_groups'] += 1
                print(f"{'[dry-run] Would delete' if dry_run else 'Deleted'} unused security group: {sg['GroupId']}")
            except Exception as e:
                print(f"Cannot delete SG {sg['GroupId']}: {str(e)}")
    
    # Clean up unused Elastic IPs
    eips = ec2.describe_addresses()
    for eip in eips['Addresses']:
        if 'InstanceId' not in eip and 'NetworkInterfaceId' not in eip:
            try:
                if not dry_run:
                    ec2.release_address(AllocationId=eip['AllocationId'])
                results['unattached_eips'] += 1
                results['estimated_savings'] += 3.65  # $0.005/hour * 24 * 30
                print(f"{'[dry-run] Would release' if dry_run else 'Released'} unused EIP: {eip['PublicIp']}")
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
