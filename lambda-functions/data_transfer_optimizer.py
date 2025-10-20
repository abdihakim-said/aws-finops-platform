import boto3
import json

def lambda_handler(event, context):
    ec2 = boto3.client('ec2')
    cloudfront = boto3.client('cloudfront')
    
    results = {
        'nat_gateway_optimization': [],
        'vpc_endpoint_recommendations': [],
        'cloudfront_opportunities': [],
        'cross_region_analysis': [],
        'potential_savings': 0
    }
    
    # Analyze NAT Gateway usage and costs
    nat_gateways = ec2.describe_nat_gateways()
    
    for nat in nat_gateways['NatGateways']:
        if nat['State'] == 'available':
            nat_id = nat['NatGatewayId']
            vpc_id = nat['VpcId']
            
            # Check if VPC has VPC endpoints that could replace NAT traffic
            vpc_endpoints = ec2.describe_vpc_endpoints(
                Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}]
            )
            
            existing_endpoints = [ep['ServiceName'] for ep in vpc_endpoints['VpcEndpoints']]
            
            # Recommend VPC endpoints for common services
            recommended_endpoints = []
            common_services = [
                'com.amazonaws.region.s3',
                'com.amazonaws.region.dynamodb',
                'com.amazonaws.region.ec2',
                'com.amazonaws.region.ssm'
            ]
            
            for service in common_services:
                service_name = service.replace('region', nat['AvailabilityZone'][:-1])
                if service_name not in existing_endpoints:
                    recommended_endpoints.append({
                        'service': service_name.split('.')[-1].upper(),
                        'estimated_savings': '$50-200/month',
                        'benefit': 'Eliminate NAT Gateway charges for this service'
                    })
            
            if recommended_endpoints:
                results['vpc_endpoint_recommendations'].append({
                    'nat_gateway_id': nat_id,
                    'vpc_id': vpc_id,
                    'current_monthly_cost': '$45 + data processing',
                    'recommended_endpoints': recommended_endpoints,
                    'potential_savings': '$100-500/month'
                })
    
    # Analyze CloudFront distribution opportunities
    try:
        distributions = cloudfront.list_distributions()
        
        # Check for origins that could benefit from CloudFront
        # This is a simplified analysis - real implementation would check ALB/S3 traffic patterns
        
        load_balancers = ec2.describe_load_balancers() if hasattr(ec2, 'describe_load_balancers') else {'LoadBalancers': []}
        
        for lb in load_balancers.get('LoadBalancers', []):
            lb_dns = lb.get('DNSName', '')
            
            # Check if this LB is already behind CloudFront
            is_cached = any(
                lb_dns in str(dist.get('Origins', {}).get('Items', []))
                for dist in distributions.get('DistributionList', {}).get('Items', [])
            )
            
            if not is_cached:
                results['cloudfront_opportunities'].append({
                    'load_balancer': lb.get('LoadBalancerName', 'Unknown'),
                    'dns_name': lb_dns,
                    'recommendation': 'Add CloudFront distribution',
                    'benefits': [
                        'Reduce origin server load',
                        'Lower data transfer costs',
                        'Improve global performance'
                    ],
                    'estimated_savings': '20-40% on data transfer'
                })
                
    except Exception as e:
        print(f"CloudFront analysis error: {str(e)}")
    
    # Cross-region data transfer analysis
    regions = ['us-east-1', 'us-west-2', 'eu-west-1', 'ap-southeast-1']
    
    for region in regions:
        try:
            regional_ec2 = boto3.client('ec2', region_name=region)
            instances = regional_ec2.describe_instances()
            
            instance_count = sum(
                len(reservation['Instances'])
                for reservation in instances['Reservations']
            )
            
            if instance_count > 0:
                results['cross_region_analysis'].append({
                    'region': region,
                    'instance_count': instance_count,
                    'recommendation': 'Consolidate workloads to reduce cross-region transfer',
                    'potential_savings': f"${instance_count * 10}-{instance_count * 50}/month"
                })
                
        except Exception as e:
            continue
    
    # Calculate total potential savings
    results['potential_savings'] = sum([
        len(results['vpc_endpoint_recommendations']) * 300,  # $300/month per NAT optimization
        len(results['cloudfront_opportunities']) * 200,     # $200/month per CloudFront optimization
        len(results['cross_region_analysis']) * 500        # $500/month per region consolidation
    ])
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
