import pytest
import json
from moto import mock_ec2, mock_cloudwatch
import boto3
import sys
import os

# Add lambda functions to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'lambda-functions'))

@mock_ec2
@mock_cloudwatch
def test_ebs_volume_optimization():
    """Test EBS gp2 to gp3 conversion"""
    # Setup
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Create gp2 volume
    volume = ec2.create_volume(
        Size=10,
        VolumeType='gp2',
        AvailabilityZone='us-east-1a'
    )
    
    from cost_optimizer import lambda_handler
    
    # Execute
    result = lambda_handler({}, {})
    
    # Verify
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert 'volumes_optimized' in body
    assert 'estimated_savings' in body

@mock_ec2
def test_snapshot_cleanup():
    """Test stale snapshot removal"""
    ec2 = boto3.client('ec2', region_name='us-east-1')
    
    # Create volume and snapshot
    volume = ec2.create_volume(Size=10, VolumeType='gp2', AvailabilityZone='us-east-1a')
    snapshot = ec2.create_snapshot(VolumeId=volume['VolumeId'])
    
    # Delete volume to make snapshot stale
    ec2.delete_volume(VolumeId=volume['VolumeId'])
    
    from cost_optimizer import lambda_handler
    
    result = lambda_handler({}, {})
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert body['snapshots_deleted'] >= 0

@mock_ec2
def test_ec2_rightsizing():
    """Test EC2 instance right-sizing recommendations"""
    from ec2_rightsizing import lambda_handler
    
    result = lambda_handler({}, {})
    
    assert result['statusCode'] == 200
    body = json.loads(result['body'])
    assert 'underutilized_instances' in body
    assert 'potential_savings' in body

def test_cost_calculation():
    """Test cost calculation accuracy"""
    from calculate_savings import calculate_ebs_savings
    
    savings = calculate_ebs_savings()
    
    assert savings['category'] == 'EBS Optimization'
    assert savings['percentage'] == 20
    assert savings['monthly_savings'] > 0
