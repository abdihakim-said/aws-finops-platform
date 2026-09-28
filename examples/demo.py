"""Offline walkthrough against a mocked AWS account (needs the dev extra: moto).

    python examples/demo.py

Creates some typical waste, scans it, previews the plan, changes the world
under the plan's feet, and shows the apply step refusing to act on stale data.
"""

import os

for key, value in {"AWS_ACCESS_KEY_ID": "demo", "AWS_SECRET_ACCESS_KEY": "demo",
                   "AWS_DEFAULT_REGION": "us-east-1", "MOTO_EC2_LOAD_DEFAULT_AMIS": "false"}.items():
    os.environ[key] = value

import boto3  # noqa: E402
from moto import mock_aws  # noqa: E402

from finops import Config, apply_plan, render, scan  # noqa: E402
from finops.checks import (  # noqa: E402
    gp2_volumes,
    idle_load_balancers,
    orphaned_snapshots,
    unattached_eips,
    unattached_volumes,
)

REGION = "us-east-1"
CHECKS = (gp2_volumes, orphaned_snapshots, unattached_eips, unattached_volumes, idle_load_balancers)
DEMO = Config(snapshot_min_age_days=0, volume_min_age_days=0, min_resource_age_days=0)

with mock_aws():
    session = boto3.Session(region_name=REGION)
    ec2 = session.client("ec2")

    image = ec2.register_image(Name="demo-image", RootDeviceName="/dev/sda1",
                               BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {"VolumeSize": 8}}])
    server = ec2.run_instances(ImageId=image["ImageId"], MinCount=1, MaxCount=1)["Instances"][0]["InstanceId"]

    # Typical waste
    big_db_disk = ec2.create_volume(Size=2000, AvailabilityZone="us-east-1a", VolumeType="gp2")["VolumeId"]
    ec2.attach_volume(VolumeId=big_db_disk, InstanceId=server, Device="/dev/sdf")
    ec2.create_volume(Size=100, AvailabilityZone="us-east-1a", VolumeType="gp2")    # left behind
    old = ec2.create_volume(Size=500, AvailabilityZone="us-east-1a", VolumeType="gp3")["VolumeId"]
    ec2.create_snapshot(VolumeId=old)
    ec2.delete_volume(VolumeId=old)
    stray_ip = ec2.allocate_address(Domain="vpc")["AllocationId"]
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnets = [ec2.create_subnet(VpcId=vpc, CidrBlock=f"10.0.{i}.0/24", AvailabilityZone=f"us-east-1{z}")
               ["Subnet"]["SubnetId"] for i, z in enumerate("ab")]
    session.client("elbv2").create_load_balancer(Name="forgotten-alb", Subnets=subnets, Type="application")

    print("=" * 100)
    print("1. SCAN (read-only)")
    print("=" * 100)
    plan = scan(session, [REGION], DEMO, checks=CHECKS)
    print(render(plan))

    print("\n" + "=" * 100)
    print("2. PREVIEW: re-check every action against live state, change nothing")
    print("=" * 100)
    for o in apply_plan(session, plan, "Jane Doe", preview=True).outcomes:
        print(f"  {o.status:<12} {o.action_id}")

    print("\n" + "=" * 100)
    print("3. THE WORLD CHANGES: someone attaches the IP and tags the big disk finops:keep")
    print("=" * 100)
    ec2.associate_address(AllocationId=stray_ip, InstanceId=server)
    ec2.create_tags(Resources=[big_db_disk], Tags=[{"Key": "finops:keep", "Value": "true"}])

    print("\n" + "=" * 100)
    print("4. APPLY as 'Jane Doe'")
    print("=" * 100)
    report = apply_plan(session, plan, "Jane Doe", expected_digest=plan.digest())
    for o in report.outcomes:
        print(f"  {o.status:<12} {o.action_id:<55} {o.reason}")
    print(f"\n  applied {report.count('applied')}, skipped {report.count('skipped')}, "
          f"failed {report.count('failed')} (approved by {report.approved_by}, plan digest {report.plan_digest})")
