import json
from datetime import timedelta

import pytest
from conftest import attached_volume, launch_instance

from finops import Config, Plan, PlanRejected, apply_plan, scan
from finops.checks import ACTIONABLE_CHECKS
from finops.model import now

REGION = "us-east-1"
NOW = Config(snapshot_min_age_days=0, volume_min_age_days=0, min_resource_age_days=0)


@pytest.fixture
def world(aws):
    """One gp2 volume, one orphaned snapshot, one free Elastic IP."""
    ec2 = aws.client("ec2")
    vol = attached_volume(ec2, 100)
    gone = ec2.create_volume(Size=8, AvailabilityZone="us-east-1a", VolumeType="gp3")["VolumeId"]
    snap = ec2.create_snapshot(VolumeId=gone)["SnapshotId"]
    ec2.delete_volume(VolumeId=gone)
    eip = ec2.allocate_address(Domain="vpc")["AllocationId"]
    plan = scan(aws, [REGION], NOW, checks=ACTIONABLE_CHECKS)
    return {"ec2": ec2, "vol": vol, "snap": snap, "eip": eip, "plan": plan, "session": aws}


def test_plan_round_trips_with_the_same_digest(world):
    plan = world["plan"]
    again = Plan.from_json(plan.to_json())
    assert again.digest() == plan.digest() and len(again.actions) == 3


def test_apply_changes_exactly_the_planned_resources(world):
    ec2 = world["ec2"]
    report = apply_plan(world["session"], world["plan"], "Jane Doe")
    assert report.count("applied") == 3 and report.count("failed") == 0
    assert ec2.describe_volumes(VolumeIds=[world["vol"]])["Volumes"][0]["VolumeType"] == "gp3"
    assert world["snap"] not in {s["SnapshotId"] for s in ec2.describe_snapshots(OwnerIds=["self"])["Snapshots"]}
    assert world["eip"] not in {a.get("AllocationId") for a in ec2.describe_addresses()["Addresses"]}


def test_preview_changes_nothing(world):
    ec2 = world["ec2"]
    report = apply_plan(world["session"], world["plan"], "Jane Doe", preview=True)
    assert report.count("would_apply") == 3
    assert ec2.describe_volumes(VolumeIds=[world["vol"]])["Volumes"][0]["VolumeType"] == "gp2"


def test_only_selected_actions_run(world):
    plan = world["plan"]
    eip_action = next(a.id for a in plan.actions if a.type == "release_address")
    report = apply_plan(world["session"], plan, "Jane Doe", only={eip_action})
    assert [o.action_id for o in report.outcomes] == [eip_action]


def test_state_changes_since_the_scan_are_respected(world):
    ec2 = world["ec2"]
    instance = launch_instance(ec2)
    ec2.associate_address(AllocationId=world["eip"], InstanceId=instance)        # EIP now in use
    ec2.create_tags(Resources=[world["vol"]], Tags=[{"Key": "finops:keep", "Value": "true"}])  # owner objects
    ec2.create_tags(Resources=[world["snap"]],                                    # AWS Backup adopted it
                    Tags=[{"Key": "aws:backup:source-resource", "Value": "x"}])
    report = apply_plan(world["session"], world["plan"], "Jane Doe")
    assert report.count("applied") == 0 and report.count("skipped") == 3
    reasons = " ".join(o.reason for o in report.outcomes)
    assert "associated" in reasons and "finops:keep" in reasons and "protected" in reasons


def test_snapshot_that_now_backs_an_ami_is_skipped():
    from finops.apply import _check_snapshot
    from finops.model import Action

    class EC2:
        def describe_snapshots(self, **_):
            return {"Snapshots": [{"SnapshotId": "snap-1", "VolumeId": "vol-gone", "Tags": []}]}

        def describe_images(self, **_):
            return {"Images": [{"ImageId": "ami-9", "BlockDeviceMappings": [{"Ebs": {"SnapshotId": "snap-1"}}]}]}

    reason = _check_snapshot(EC2(), Action("delete_snapshot", "us-east-1", "snap-1"))
    assert reason == "snapshot now backs AMI ami-9"


def test_snapshot_is_kept_if_volume_lookup_fails_for_any_other_reason():
    from botocore.exceptions import ClientError

    from finops.apply import _check_snapshot
    from finops.model import Action

    class EC2:
        def describe_snapshots(self, **_):
            return {"Snapshots": [{"SnapshotId": "snap-1", "VolumeId": "vol-x", "Tags": []}]}

        def describe_images(self, **_):
            return {"Images": []}

        def describe_volumes(self, **_):
            error = {"Error": {"Code": "RequestLimitExceeded", "Message": "slow down"}}
            raise ClientError(error, "DescribeVolumes")

    reason = _check_snapshot(EC2(), Action("delete_snapshot", "us-east-1", "snap-1"))
    assert "could not confirm" in reason and "RequestLimitExceeded" in reason


def test_expired_plan_is_rejected(world):
    plan = world["plan"]
    plan.expires_at = (now() - timedelta(minutes=1)).isoformat()
    with pytest.raises(PlanRejected, match="expired"):
        apply_plan(world["session"], plan, "Jane Doe")


def test_tampered_plan_is_rejected(world):
    approved = world["plan"].digest()
    raw = json.loads(world["plan"].to_json())
    raw["findings"][0]["action"]["resource_id"] = "vol-someone-elses"
    tampered = Plan.from_json(json.dumps(raw))
    with pytest.raises(PlanRejected, match="digest"):
        apply_plan(world["session"], tampered, "Jane Doe", expected_digest=approved)


def test_approver_and_account_are_required(world):
    with pytest.raises(PlanRejected, match="approver"):
        apply_plan(world["session"], world["plan"], "  ")
    world["plan"].account_id = "999999999999"
    with pytest.raises(PlanRejected, match="account"):
        apply_plan(world["session"], world["plan"], "Jane Doe")


def test_unknown_action_ids_are_rejected(world):
    with pytest.raises(PlanRejected, match="not in the plan"):
        apply_plan(world["session"], world["plan"], "Jane Doe", only={"delete_snapshot:us-east-1:snap-nope"})
