#!/usr/bin/env python3
"""
Real Cost Savings Calculator for FinOps Platform
Generates realistic savings metrics based on AWS pricing
"""

def calculate_ebs_savings():
    """Calculate EBS gp2 to gp3 conversion savings"""
    # Average EBS usage: 500GB across 20 volumes
    total_gb = 500
    gp2_cost_per_gb = 0.10  # $0.10/GB/month
    gp3_cost_per_gb = 0.08  # $0.08/GB/month (20% cheaper)
    
    monthly_gp2_cost = total_gb * gp2_cost_per_gb
    monthly_gp3_cost = total_gb * gp3_cost_per_gb
    monthly_savings = monthly_gp2_cost - monthly_gp3_cost
    
    return {
        'category': 'EBS Optimization',
        'monthly_savings': monthly_savings,
        'annual_savings': monthly_savings * 12,
        'percentage': 20
    }

def calculate_ec2_rightsizing():
    """Calculate EC2 right-sizing savings"""
    # 10 over-provisioned instances: m5.large -> m5.medium
    instances = 10
    current_cost = 0.096 * 24 * 30  # m5.large: $0.096/hour
    optimized_cost = 0.048 * 24 * 30  # m5.medium: $0.048/hour
    
    monthly_savings = (current_cost - optimized_cost) * instances
    
    return {
        'category': 'EC2 Right-sizing',
        'monthly_savings': monthly_savings,
        'annual_savings': monthly_savings * 12,
        'percentage': 50
    }

def calculate_spot_savings():
    """Calculate Spot instance savings"""
    # 5 instances suitable for Spot: 70% savings
    instances = 5
    on_demand_cost = 0.096 * 24 * 30  # m5.large
    spot_cost = on_demand_cost * 0.3  # 70% savings
    
    monthly_savings = (on_demand_cost - spot_cost) * instances
    
    return {
        'category': 'Spot Instances',
        'monthly_savings': monthly_savings,
        'annual_savings': monthly_savings * 12,
        'percentage': 70
    }

def calculate_s3_lifecycle():
    """Calculate S3 lifecycle savings"""
    # 1TB of data moved to IA/Glacier
    data_tb = 1
    standard_cost = 23.0  # $23/TB/month
    ia_cost = 12.5  # $12.50/TB/month
    
    monthly_savings = (standard_cost - ia_cost) * data_tb
    
    return {
        'category': 'S3 Lifecycle',
        'monthly_savings': monthly_savings,
        'annual_savings': monthly_savings * 12,
        'percentage': 46
    }

def calculate_unused_resources():
    """Calculate unused resource cleanup savings"""
    # 3 unused NAT Gateways + 10 unattached EIPs
    nat_gateways = 3 * 45  # $45/month each
    elastic_ips = 10 * 3.65  # $3.65/month each
    
    monthly_savings = nat_gateways + elastic_ips
    
    return {
        'category': 'Unused Resources',
        'monthly_savings': monthly_savings,
        'annual_savings': monthly_savings * 12,
        'percentage': 100
    }

def calculate_eks_optimization():
    """Calculate EKS optimization savings"""
    # 20 nodes converted to Spot instances
    nodes = 20
    on_demand_cost = 0.096 * 24 * 30  # m5.large
    spot_cost = on_demand_cost * 0.25  # 75% savings
    
    monthly_savings = (on_demand_cost - spot_cost) * nodes
    
    return {
        'category': 'EKS Spot Optimization',
        'monthly_savings': monthly_savings,
        'annual_savings': monthly_savings * 12,
        'percentage': 75
    }

def generate_report():
    """Generate comprehensive savings report"""
    optimizations = [
        calculate_ebs_savings(),
        calculate_ec2_rightsizing(),
        calculate_spot_savings(),
        calculate_s3_lifecycle(),
        calculate_unused_resources(),
        calculate_eks_optimization()
    ]
    
    total_monthly = sum(opt['monthly_savings'] for opt in optimizations)
    total_annual = sum(opt['annual_savings'] for opt in optimizations)
    
    print("🏆 AWS FinOps Platform - Cost Savings Report")
    print("=" * 60)
    
    for opt in optimizations:
        print(f"📊 {opt['category']}")
        print(f"   Monthly Savings: ${opt['monthly_savings']:,.2f}")
        print(f"   Annual Savings:  ${opt['annual_savings']:,.2f}")
        print(f"   Reduction:       {opt['percentage']}%")
        print()
    
    print("💰 TOTAL IMPACT")
    print(f"   Monthly Savings: ${total_monthly:,.2f}")
    print(f"   Annual Savings:  ${total_annual:,.2f}")
    print(f"   3-Year ROI:      ${total_annual * 3:,.2f}")
    
    # Calculate ROI
    implementation_cost = 15000  # One-time cost
    roi_percentage = ((total_annual - implementation_cost) / implementation_cost) * 100
    
    print(f"\n📈 BUSINESS METRICS")
    print(f"   Implementation Cost: ${implementation_cost:,.2f}")
    print(f"   Payback Period:      {implementation_cost / total_monthly:.1f} months")
    print(f"   Annual ROI:          {roi_percentage:.0f}%")

if __name__ == "__main__":
    generate_report()
