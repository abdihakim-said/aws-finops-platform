import boto3
import json
from datetime import datetime, timedelta

def lambda_handler(event, context):
    ce = boto3.client('ce')  # Cost Explorer
    ec2 = boto3.client('ec2')
    
    results = {
        'ri_recommendations': [],
        'underutilized_ris': [],
        'potential_savings': 0,
        'coverage_analysis': {}
    }
    
    # Get RI utilization for last 30 days
    ri_utilization = ce.get_reservation_utilization(
        TimePeriod={
            'Start': (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d'),
            'End': datetime.now().strftime('%Y-%m-%d')
        },
        GroupBy=[
            {'Type': 'DIMENSION', 'Key': 'INSTANCE_TYPE'},
            {'Type': 'DIMENSION', 'Key': 'AVAILABILITY_ZONE'}
        ]
    )
    
    # Analyze underutilized RIs
    for group in ri_utilization['UtilizationsByTime']:
        for reservation in group['Groups']:
            utilization = float(reservation['Attributes']['UtilizationPercentage'])
            if utilization < 80:  # Underutilized threshold
                results['underutilized_ris'].append({
                    'instance_type': reservation['Keys'][0],
                    'availability_zone': reservation['Keys'][1],
                    'utilization': f"{utilization:.1f}%",
                    'recommendation': 'Consider modifying or selling RI'
                })
    
    # Get RI recommendations from Cost Explorer
    ri_recommendations_response = ce.get_rightsizing_recommendation(
        Service='AmazonEC2'
    )
    
    for rec in ri_recommendations_response.get('RightsizingRecommendations', []):
        if rec['RightsizingType'] == 'Terminate':
            continue
            
        current_instance = rec['CurrentInstance']
        recommended_instance = rec['ModifyRecommendationDetail']['TargetInstances'][0]
        
        estimated_savings = float(rec['EstimatedMonthlySavings'])
        
        results['ri_recommendations'].append({
            'account_id': current_instance['ResourceId'].split(':')[4],
            'current_type': current_instance['InstanceName'],
            'recommended_type': recommended_instance['InstanceName'],
            'monthly_savings': estimated_savings,
            'annual_savings': estimated_savings * 12
        })
        
        results['potential_savings'] += estimated_savings * 12
    
    # Calculate RI coverage
    coverage = ce.get_reservation_coverage(
        TimePeriod={
            'Start': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
            'End': datetime.now().strftime('%Y-%m-%d')
        }
    )
    
    total_coverage = coverage['CoveragesByTime'][0]['Total']
    results['coverage_analysis'] = {
        'coverage_percentage': f"{float(total_coverage['CoverageHours']['CoverageHoursPercentage']):.1f}%",
        'on_demand_cost': f"${float(total_coverage['OnDemandCost']):.2f}",
        'covered_cost': f"${float(total_coverage['CoveredHours']['CoveredHoursCost']):.2f}"
    }
    
    return {
        'statusCode': 200,
        'body': json.dumps(results, default=str)
    }
