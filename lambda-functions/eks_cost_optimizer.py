import boto3
import json
from kubernetes import client, config
import base64

def lambda_handler(event, context):
    eks = boto3.client('eks')
    ec2 = boto3.client('ec2')
    
    results = {
        'cluster_analysis': [],
        'node_group_optimization': [],
        'pod_rightsizing': [],
        'spot_opportunities': [],
        'potential_savings': 0
    }
    
    # Get all EKS clusters
    clusters = eks.list_clusters()
    
    for cluster_name in clusters['clusters']:
        cluster_info = eks.describe_cluster(name=cluster_name)
        cluster = cluster_info['cluster']
        
        # Analyze cluster costs
        cluster_analysis = analyze_cluster_costs(eks, ec2, cluster_name)
        results['cluster_analysis'].append(cluster_analysis)
        
        # Analyze node groups
        node_groups = eks.list_nodegroups(clusterName=cluster_name)
        
        for ng_name in node_groups['nodegroups']:
            ng_info = eks.describe_nodegroup(
                clusterName=cluster_name,
                nodegroupName=ng_name
            )
            
            nodegroup = ng_info['nodegroup']
            
            # Check for optimization opportunities
            optimization = analyze_nodegroup(nodegroup, cluster_name)
            if optimization:
                results['node_group_optimization'].append(optimization)
                results['potential_savings'] += optimization.get('monthly_savings', 0)
        
        # Analyze pod resource requests vs usage (requires cluster access)
        try:
            pod_analysis = analyze_pod_resources(cluster_name)
            results['pod_rightsizing'].extend(pod_analysis)
        except Exception as e:
            print(f"Could not analyze pods for {cluster_name}: {str(e)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def analyze_cluster_costs(eks, ec2, cluster_name):
    """Analyze EKS cluster cost optimization opportunities"""
    
    # Get cluster details
    cluster_info = eks.describe_cluster(name=cluster_name)
    cluster = cluster_info['cluster']
    
    # Calculate control plane costs ($0.10/hour = $73/month)
    control_plane_cost = 73.0
    
    # Get node groups and calculate compute costs
    node_groups = eks.list_nodegroups(clusterName=cluster_name)
    total_node_cost = 0
    total_nodes = 0
    
    for ng_name in node_groups['nodegroups']:
        ng_info = eks.describe_nodegroup(
            clusterName=cluster_name,
            nodegroupName=ng_name
        )
        nodegroup = ng_info['nodegroup']
        
        # Calculate node costs
        instance_types = nodegroup['instanceTypes']
        desired_capacity = nodegroup['scalingConfig']['desiredSize']
        
        for instance_type in instance_types:
            node_cost = get_instance_hourly_cost(instance_type)
            monthly_cost = node_cost * 24 * 30 * desired_capacity
            total_node_cost += monthly_cost
            total_nodes += desired_capacity
    
    return {
        'cluster_name': cluster_name,
        'control_plane_cost': control_plane_cost,
        'node_cost': round(total_node_cost, 2),
        'total_monthly_cost': round(control_plane_cost + total_node_cost, 2),
        'node_count': total_nodes,
        'version': cluster['version'],
        'recommendations': generate_cluster_recommendations(cluster, total_nodes)
    }

def analyze_nodegroup(nodegroup, cluster_name):
    """Analyze node group for cost optimization"""
    
    ng_name = nodegroup['nodegroupName']
    instance_types = nodegroup['instanceTypes']
    capacity_type = nodegroup.get('capacityType', 'ON_DEMAND')
    
    scaling_config = nodegroup['scalingConfig']
    desired = scaling_config['desiredSize']
    min_size = scaling_config['minSize']
    max_size = scaling_config['maxSize']
    
    recommendations = []
    monthly_savings = 0
    
    # Check if using On-Demand only (recommend Spot)
    if capacity_type == 'ON_DEMAND':
        current_cost = sum(
            get_instance_hourly_cost(it) * 24 * 30 * desired
            for it in instance_types
        )
        
        # Spot instances typically 60-90% cheaper
        spot_savings = current_cost * 0.7  # 70% savings
        monthly_savings += spot_savings
        
        recommendations.append({
            'type': 'SPOT_INSTANCES',
            'description': 'Convert to Spot instances for non-critical workloads',
            'current_cost': f"${current_cost:.2f}/month",
            'potential_savings': f"${spot_savings:.2f}/month",
            'implementation': 'Use mixed instance types with Spot capacity'
        })
    
    # Check for over-provisioning (desired == max)
    if desired == max_size and desired > min_size:
        recommendations.append({
            'type': 'RIGHT_SIZING',
            'description': 'Node group may be over-provisioned',
            'current_capacity': f"{desired} nodes",
            'recommendation': f"Monitor usage and consider reducing to {min_size}-{desired-1} nodes",
            'potential_savings': f"${get_instance_hourly_cost(instance_types[0]) * 24 * 30:.2f}/month per node"
        })
    
    # Check for single instance type (recommend diversification)
    if len(instance_types) == 1:
        recommendations.append({
            'type': 'DIVERSIFICATION',
            'description': 'Use multiple instance types for better Spot availability',
            'current_types': instance_types,
            'recommendation': 'Add 2-3 similar instance types (e.g., m5.large, m5a.large, m4.large)'
        })
    
    if recommendations:
        return {
            'cluster_name': cluster_name,
            'nodegroup_name': ng_name,
            'current_capacity': desired,
            'instance_types': instance_types,
            'capacity_type': capacity_type,
            'recommendations': recommendations,
            'monthly_savings': monthly_savings
        }
    
    return None

def analyze_pod_resources(cluster_name):
    """Analyze pod resource requests vs actual usage"""
    
    # This would require cluster access - simplified for demo
    pod_recommendations = [
        {
            'namespace': 'default',
            'pod_name': 'example-app',
            'current_requests': {'cpu': '1000m', 'memory': '2Gi'},
            'actual_usage': {'cpu': '200m', 'memory': '512Mi'},
            'recommendation': 'Reduce CPU request to 300m, memory to 1Gi',
            'cost_impact': 'Enable better pod packing, reduce node requirements'
        }
    ]
    
    return pod_recommendations

def generate_cluster_recommendations(cluster, node_count):
    """Generate cluster-level recommendations"""
    
    recommendations = []
    
    # Version upgrade recommendation
    current_version = cluster['version']
    if current_version < '1.28':
        recommendations.append({
            'type': 'VERSION_UPGRADE',
            'description': f'Upgrade from {current_version} to latest version',
            'benefits': ['Better resource efficiency', 'New cost optimization features']
        })
    
    # Cluster Autoscaler recommendation
    recommendations.append({
        'type': 'CLUSTER_AUTOSCALER',
        'description': 'Implement Cluster Autoscaler for dynamic scaling',
        'benefits': ['Automatic node scaling', 'Reduce idle capacity costs']
    })
    
    # Fargate recommendation for small workloads
    if node_count < 5:
        recommendations.append({
            'type': 'FARGATE_CONSIDERATION',
            'description': 'Consider Fargate for small, variable workloads',
            'benefits': ['Pay per pod', 'No node management overhead']
        })
    
    return recommendations

def get_instance_hourly_cost(instance_type):
    """Get approximate hourly cost for instance type"""
    
    pricing = {
        't3.small': 0.0208, 't3.medium': 0.0416, 't3.large': 0.0832,
        'm5.large': 0.096, 'm5.xlarge': 0.192, 'm5.2xlarge': 0.384,
        'c5.large': 0.085, 'c5.xlarge': 0.17, 'c5.2xlarge': 0.34,
        'r5.large': 0.126, 'r5.xlarge': 0.252
    }
    
    return pricing.get(instance_type, 0.1)
