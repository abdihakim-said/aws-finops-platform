import boto3
import json

def lambda_handler(event, context):
    """
    Kubernetes resource optimization recommendations
    Focuses on cost optimization without requiring direct cluster access
    """
    
    results = {
        'resource_recommendations': [],
        'cost_optimization_strategies': [],
        'monitoring_suggestions': [],
        'potential_savings': 0
    }
    
    # General Kubernetes cost optimization recommendations
    results['resource_recommendations'] = [
        {
            'category': 'Resource Requests & Limits',
            'recommendations': [
                {
                    'issue': 'Over-provisioned CPU requests',
                    'solution': 'Set CPU requests to 80% of actual usage',
                    'impact': '20-40% better pod density',
                    'implementation': 'Use VPA (Vertical Pod Autoscaler) for recommendations'
                },
                {
                    'issue': 'Missing memory limits',
                    'solution': 'Set memory limits to prevent OOM kills',
                    'impact': 'Prevent node instability, better scheduling',
                    'implementation': 'Add memory limits based on monitoring data'
                }
            ]
        },
        {
            'category': 'Node Optimization',
            'recommendations': [
                {
                    'issue': 'Single instance type node groups',
                    'solution': 'Use mixed instance types for Spot diversity',
                    'impact': '60-90% cost reduction with Spot instances',
                    'implementation': 'Configure 3+ instance types in node groups'
                },
                {
                    'issue': 'Static node capacity',
                    'solution': 'Implement Cluster Autoscaler',
                    'impact': '30-50% reduction in idle capacity costs',
                    'implementation': 'Deploy cluster-autoscaler with proper node group tags'
                }
            ]
        }
    ]
    
    # Cost optimization strategies
    results['cost_optimization_strategies'] = [
        {
            'strategy': 'Spot Instance Integration',
            'description': 'Use Spot instances for fault-tolerant workloads',
            'savings': '60-90%',
            'implementation_steps': [
                'Identify stateless applications',
                'Configure node groups with Spot capacity',
                'Implement graceful pod termination',
                'Use Pod Disruption Budgets'
            ],
            'best_practices': [
                'Mix On-Demand and Spot (20/80 ratio)',
                'Use multiple AZs and instance types',
                'Monitor Spot interruption rates'
            ]
        },
        {
            'strategy': 'Right-sizing Workloads',
            'description': 'Optimize resource requests based on actual usage',
            'savings': '20-40%',
            'implementation_steps': [
                'Deploy metrics-server and VPA',
                'Monitor resource usage for 1-2 weeks',
                'Apply VPA recommendations gradually',
                'Set up resource quotas per namespace'
            ],
            'tools': [
                'Vertical Pod Autoscaler (VPA)',
                'Kubernetes Resource Recommender',
                'Prometheus + Grafana for monitoring'
            ]
        },
        {
            'strategy': 'Fargate for Variable Workloads',
            'description': 'Use Fargate for unpredictable or small workloads',
            'savings': '30-60% for variable workloads',
            'use_cases': [
                'CI/CD pipelines',
                'Batch processing jobs',
                'Development environments',
                'Microservices with variable traffic'
            ],
            'considerations': [
                'Higher per-vCPU cost than EC2',
                'No persistent storage',
                'Limited to specific instance sizes'
            ]
        }
    ]
    
    # Monitoring and governance
    results['monitoring_suggestions'] = [
        {
            'tool': 'Kubecost',
            'purpose': 'Real-time cost allocation and optimization',
            'features': [
                'Per-pod, namespace, and service cost breakdown',
                'Right-sizing recommendations',
                'Spot instance savings tracking',
                'Multi-cluster cost visibility'
            ]
        },
        {
            'tool': 'AWS Cost Explorer',
            'purpose': 'EKS service-level cost analysis',
            'features': [
                'EKS control plane costs',
                'EC2 instance costs by cluster',
                'Data transfer costs',
                'Reserved Instance recommendations'
            ]
        },
        {
            'tool': 'Prometheus + Grafana',
            'purpose': 'Resource utilization monitoring',
            'metrics': [
                'CPU and memory utilization',
                'Pod scheduling efficiency',
                'Node capacity utilization',
                'Cost per application/team'
            ]
        }
    ]
    
    # Calculate potential savings
    results['potential_savings'] = calculate_k8s_savings()
    
    # Add specific EKS cost optimization checklist
    results['eks_optimization_checklist'] = [
        {
            'category': 'Compute',
            'items': [
                '✓ Use Spot instances for 70%+ of workloads',
                '✓ Implement Cluster Autoscaler',
                '✓ Right-size node groups based on workload requirements',
                '✓ Use mixed instance types for better Spot availability'
            ]
        },
        {
            'category': 'Storage',
            'items': [
                '✓ Use gp3 EBS volumes instead of gp2',
                '✓ Implement storage classes for different performance needs',
                '✓ Clean up unused PVCs and snapshots',
                '✓ Use EFS for shared storage only when necessary'
            ]
        },
        {
            'category': 'Networking',
            'items': [
                '✓ Use VPC endpoints to reduce NAT Gateway costs',
                '✓ Optimize load balancer usage (ALB vs NLB)',
                '✓ Monitor cross-AZ data transfer costs',
                '✓ Use cluster-internal communication when possible'
            ]
        }
    ]
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }

def calculate_k8s_savings():
    """Calculate potential Kubernetes cost savings"""
    
    # Example calculation for a medium-sized cluster
    baseline_monthly_cost = 15000  # $15k/month
    
    savings_breakdown = {
        'spot_instances': baseline_monthly_cost * 0.60,  # 60% savings
        'right_sizing': baseline_monthly_cost * 0.25,   # 25% savings
        'autoscaling': baseline_monthly_cost * 0.20,    # 20% savings
        'storage_optimization': baseline_monthly_cost * 0.10  # 10% savings
    }
    
    # Total potential savings (not additive due to overlaps)
    total_potential = baseline_monthly_cost * 0.70  # 70% total potential
    
    return {
        'baseline_monthly_cost': baseline_monthly_cost,
        'savings_breakdown': savings_breakdown,
        'total_potential_monthly_savings': total_potential,
        'annual_savings_potential': total_potential * 12
    }
