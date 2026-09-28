from datetime import datetime, timezone

import pytest
from botocore.exceptions import ClientError
from conftest import attached_volume, launch_instance

from finops import Config, scan
from finops.checks import (
    ec2_rightsizing,
    gp2_volumes,
    gp3_equivalent,
    idle_load_balancers,
    idle_rds,
    orphaned_snapshots,
    s3_stale_multipart_uploads,
    unattached_eips,
    unattached_volumes,
)
from finops.prices import Prices

REGION = "us-east-1"
NOW = Config(snapshot_min_age_days=0, volume_min_age_days=0, multipart_min_age_days=0, min_resource_age_days=0)
P = Prices()


def ids(findings):
    return {f.resource_id for f in findings}


# ---- gp2 -> gp3 -------------------------------------------------------------

@pytest.mark.parametrize("size,iops,throughput", [
    (10, 3000, 125),        # small: gp3 baseline already beats gp2's 100 IOPS
    (170, 3000, 125),
    (171, 3000, 250),       # over 170 GiB gp2 gets up to 250 MiB/s
    (2000, 6000, 250),      # gp2 gives 3 IOPS/GB, so provision 6,000 to match
    (6000, 16000, 250),     # gp2 caps at 16,000 IOPS
])
def test_gp3_matches_gp2_performance(size, iops, throughput):
    assert gp3_equivalent(size) == (iops, throughput)


def test_gp2_finding_keeps_performance_and_prices_the_extra_iops(aws):
    ec2 = aws.client("ec2")
    big = attached_volume(ec2, 2000)
    attached_volume(ec2, 50, "gp3")
    ec2.create_volume(Size=300, AvailabilityZone="us-east-1a", VolumeType="gp2")   # unattached: report instead
    [f] = gp2_volumes(aws, REGION, NOW, P)
    assert f.resource_id == big
    assert f.action.params == {"VolumeType": "gp3", "Iops": 6000, "Throughput": 250}
    # gp2 $200 vs gp3 $160 + 3,000 extra IOPS ($15) + 125 extra MiB/s ($5)
    assert f.monthly_saving_usd == 20.0


def test_kept_volume_is_ignored(aws):
    ec2 = aws.client("ec2")
    attached_volume(ec2, 100, TagSpecifications=[{"ResourceType": "volume",
                                                  "Tags": [{"Key": "finops:keep", "Value": "true"}]}])
    assert gp2_volumes(aws, REGION, NOW, P) == []


# ---- snapshots ----------------------------------------------------------------

def test_only_true_orphans_are_flagged(aws):
    ec2 = aws.client("ec2")
    live = ec2.create_volume(Size=8, AvailabilityZone="us-east-1a")["VolumeId"]
    gone = ec2.create_volume(Size=8, AvailabilityZone="us-east-1a")["VolumeId"]
    keep_vol = ec2.create_volume(Size=8, AvailabilityZone="us-east-1a")["VolumeId"]

    of_live = ec2.create_snapshot(VolumeId=live)["SnapshotId"]
    orphan = ec2.create_snapshot(VolumeId=gone)["SnapshotId"]
    backup = ec2.create_snapshot(VolumeId=gone, TagSpecifications=[{
        "ResourceType": "snapshot", "Tags": [{"Key": "aws:backup:source-resource", "Value": "x"}]}])["SnapshotId"]
    kept = ec2.create_snapshot(VolumeId=keep_vol, TagSpecifications=[{
        "ResourceType": "snapshot", "Tags": [{"Key": "finops:keep", "Value": "true"}]}])["SnapshotId"]
    image = ec2.register_image(Name="golden", RootDeviceName="/dev/sda1",
                               BlockDeviceMappings=[{"DeviceName": "/dev/sda1", "Ebs": {"SnapshotId": orphan}}])
    # moto gives the image its own snapshot (whose volume doesn't exist); on AWS it would reuse ours
    ami_backing = ec2.describe_images(ImageIds=[image["ImageId"]])["Images"][0][
        "BlockDeviceMappings"][0]["Ebs"]["SnapshotId"]
    ec2.delete_volume(VolumeId=gone)
    ec2.delete_volume(VolumeId=keep_vol)

    found = orphaned_snapshots(aws, REGION, NOW, P)
    assert ids(found) == {orphan}
    assert not {of_live, ami_backing, backup, kept} & ids(found)
    assert found[0].monthly_saving_usd is None          # incremental size is unknown
    assert found[0].detail["upper_bound_usd"] == 0.4    # 8 GiB x $0.05


def test_young_snapshots_are_left_alone(aws):
    ec2 = aws.client("ec2")
    vol = ec2.create_volume(Size=8, AvailabilityZone="us-east-1a")["VolumeId"]
    ec2.create_snapshot(VolumeId=vol)
    ec2.delete_volume(VolumeId=vol)
    assert orphaned_snapshots(aws, REGION, Config(snapshot_min_age_days=30), P) == []


# ---- Elastic IPs and volumes ---------------------------------------------------

def test_unattached_eip(aws):
    ec2 = aws.client("ec2")
    free = ec2.allocate_address(Domain="vpc")["AllocationId"]
    used = ec2.allocate_address(Domain="vpc")["AllocationId"]
    instance = launch_instance(ec2)
    ec2.associate_address(AllocationId=used, InstanceId=instance)
    [f] = unattached_eips(aws, REGION, NOW, P)
    assert f.resource_id == free and f.monthly_saving_usd == 3.65


def test_unattached_volume_is_report_only(aws):
    ec2 = aws.client("ec2")
    ec2.create_volume(Size=100, AvailabilityZone="us-east-1a", VolumeType="gp3")
    [f] = unattached_volumes(aws, REGION, NOW, P)
    assert f.action is None and f.monthly_saving_usd == 8.0


# ---- idle load balancers and databases ------------------------------------------

def _alb(aws):
    ec2, elb = aws.client("ec2"), aws.client("elbv2")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnets = [ec2.create_subnet(VpcId=vpc, CidrBlock=f"10.0.{i}.0/24", AvailabilityZone=f"us-east-1{az}")
               ["Subnet"]["SubnetId"] for i, az in enumerate("ab")]
    lb = elb.create_load_balancer(Name="quiet-alb", Subnets=subnets, Type="application")["LoadBalancers"][0]
    return lb


def test_alb_with_no_requests_is_idle(aws):
    _alb(aws)
    [f] = idle_load_balancers(aws, REGION, NOW, P)
    assert f.resource_id == "quiet-alb" and f.action is None and f.monthly_saving_usd == 16.43


def test_alb_with_requests_is_not_idle(aws):
    lb = _alb(aws)
    aws.client("cloudwatch").put_metric_data(Namespace="AWS/ApplicationELB", MetricData=[{
        "MetricName": "RequestCount", "Value": 42, "Timestamp": datetime.now(timezone.utc),
        "Dimensions": [{"Name": "LoadBalancer", "Value": lb["LoadBalancerArn"].split(":loadbalancer/")[1]}]}])
    assert idle_load_balancers(aws, REGION, NOW, P) == []


def _db(aws, name):
    aws.client("rds").create_db_instance(DBInstanceIdentifier=name, DBInstanceClass="db.t3.medium",
                                         Engine="postgres", AllocatedStorage=20, MasterUsername="admin",
                                         MasterUserPassword="not-a-real-password")


def _connections(aws, name, value):
    aws.client("cloudwatch").put_metric_data(Namespace="AWS/RDS", MetricData=[{
        "MetricName": "DatabaseConnections", "Value": value, "Timestamp": datetime.now(timezone.utc),
        "Dimensions": [{"Name": "DBInstanceIdentifier", "Value": name}]}])


def test_rds_idle_only_with_evidence(aws):
    _db(aws, "unused-db")
    _db(aws, "busy-db")
    _db(aws, "no-metrics-db")
    _connections(aws, "unused-db", 0)
    _connections(aws, "busy-db", 3)
    assert ids(idle_rds(aws, REGION, NOW, P)) == {"unused-db"}   # missing metrics != idle


# ---- rightsizing and S3 ----------------------------------------------------------

def test_rightsizing_uses_compute_optimizer(aws, stub_session):
    session = stub_session(aws, recommendations=[
        {"instanceArn": "arn:aws:ec2:us-east-1:123456789012:instance/i-over", "finding": "OVER_PROVISIONED",
         "currentInstanceType": "m5.2xlarge",
         "recommendationOptions": [
             {"rank": 2, "instanceType": "m5.xlarge"},
             {"rank": 1, "instanceType": "m6i.large",
              "savingsOpportunity": {"estimatedMonthlySavings": {"value": 210.24}}}]},
        {"instanceArn": "arn:aws:ec2:us-east-1:123456789012:instance/i-ok", "finding": "OPTIMIZED",
         "currentInstanceType": "t3.small", "recommendationOptions": []},
    ])
    [f] = ec2_rightsizing(session, REGION, NOW, P)
    assert f.resource_id == "i-over" and "m6i.large" in f.summary and f.monthly_saving_usd == 210.24


def test_compute_optimizer_not_enabled_becomes_a_note(aws, stub_session):
    err = ClientError({"Error": {"Code": "OptInRequiredException", "Message": "opt in"}},
                      "GetEC2InstanceRecommendations")
    plan = scan(stub_session(aws, error=err), [REGION], NOW)
    assert any("Compute Optimizer is not enabled" in n for n in plan.notes)


def test_stale_multipart_uploads(aws):
    s3 = aws.client("s3")
    s3.create_bucket(Bucket="uploads-without-rule")
    s3.create_bucket(Bucket="uploads-with-rule")
    s3.put_bucket_lifecycle_configuration(Bucket="uploads-with-rule", LifecycleConfiguration={"Rules": [{
        "ID": "abort", "Status": "Enabled", "Filter": {"Prefix": ""},
        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7}}]})
    for b in ("uploads-without-rule", "uploads-with-rule"):
        s3.create_multipart_upload(Bucket=b, Key="big.bin")
    assert ids(s3_stale_multipart_uploads(aws, REGION, NOW, P)) == {"uploads-without-rule"}


# ---- whole scan ---------------------------------------------------------------------

def test_scan_orders_actionable_first_and_totals(aws, stub_session):
    ec2 = aws.client("ec2")
    attached_volume(ec2, 500)
    ec2.allocate_address(Domain="vpc")
    plan = scan(stub_session(aws), [REGION], NOW)
    assert [f.check for f in plan.findings][:2] == ["gp2_volume", "unattached_eip"]
    # 500 GiB: gp2 $50 -> gp3 $40 + 125 MiB/s extra throughput ($5) = $5 saved; EIP $3.65
    assert plan.total_saving(actionable_only=True) == pytest.approx(5.0 + 3.65)
    assert plan.account_id == "123456789012"
