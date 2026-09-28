"""Apply an approved plan.

Only actions that are in the plan can run, the plan must not have expired,
and every action is re-checked against the live resource first: a snapshot
whose volume came back, or an Elastic IP that got attached since the scan,
is skipped rather than acted on.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from botocore.exceptions import ClientError

from .checks import MANAGED_SNAPSHOT_TAGS
from .model import Action, Plan, is_kept, now, tags_of


class PlanRejected(Exception):
    pass


@dataclass
class Outcome:
    action_id: str
    status: str   # applied | would_apply | skipped | failed
    reason: str = ""


@dataclass
class ApplyReport:
    plan_id: str
    plan_digest: str
    approved_by: str
    approved_at: str
    preview: bool
    outcomes: list[Outcome] = field(default_factory=list)

    def count(self, status: str) -> int:
        return sum(o.status == status for o in self.outcomes)


def _code(e: ClientError) -> str:
    return e.response["Error"]["Code"]


def _check_volume(ec2, a: Action) -> str | None:
    try:
        vol = ec2.describe_volumes(VolumeIds=[a.resource_id])["Volumes"][0]
    except ClientError as e:
        return f"volume not found ({_code(e)})"
    if vol["VolumeType"] != "gp2":
        return f"volume is now {vol['VolumeType']}"
    if is_kept(vol):
        return "volume is tagged finops:keep"
    return None


def _check_snapshot(ec2, a: Action) -> str | None:
    try:
        snap = ec2.describe_snapshots(SnapshotIds=[a.resource_id])["Snapshots"][0]
    except ClientError as e:
        return f"snapshot not found ({_code(e)})"
    tags = tags_of(snap)
    if is_kept(snap) or any(t in tags for t in MANAGED_SNAPSHOT_TAGS):
        return "snapshot is now protected by a tag"
    for image in ec2.describe_images(Owners=["self"])["Images"]:
        if any(m.get("Ebs", {}).get("SnapshotId") == a.resource_id for m in image.get("BlockDeviceMappings", [])):
            return f"snapshot now backs AMI {image['ImageId']}"
    try:
        ec2.describe_volumes(VolumeIds=[snap["VolumeId"]])
        return f"source volume {snap['VolumeId']} exists again"
    except ClientError as e:
        if _code(e) != "InvalidVolume.NotFound":
            return f"could not confirm the source volume is gone ({_code(e)})"
    return None


def _check_address(ec2, a: Action) -> str | None:
    try:
        addr = ec2.describe_addresses(AllocationIds=[a.resource_id])["Addresses"][0]
    except ClientError as e:
        return f"address not found ({_code(e)})"
    if "AssociationId" in addr:
        return "address is now associated"
    if is_kept(addr):
        return "address is tagged finops:keep"
    return None


HANDLERS = {
    "modify_volume": (_check_volume, lambda ec2, a: ec2.modify_volume(VolumeId=a.resource_id, **a.params)),
    "delete_snapshot": (_check_snapshot, lambda ec2, a: ec2.delete_snapshot(SnapshotId=a.resource_id)),
    "release_address": (_check_address, lambda ec2, a: ec2.release_address(AllocationId=a.resource_id)),
}


def apply_plan(session, plan: Plan, approved_by: str, *, expected_digest: str | None = None,
               only: set[str] | None = None, preview: bool = False) -> ApplyReport:
    if not approved_by.strip():
        raise PlanRejected("an approver name is required")
    if plan.expired():
        raise PlanRejected(f"plan {plan.plan_id} expired at {plan.expires_at}; run a new scan")
    digest = plan.digest()
    if expected_digest is not None and expected_digest != digest:
        raise PlanRejected("plan digest does not match what was approved")
    account = session.client("sts").get_caller_identity()["Account"]
    if account != plan.account_id:
        raise PlanRejected(f"plan is for account {plan.account_id}, credentials are for {account}")

    report = ApplyReport(plan.plan_id, digest, approved_by, now().isoformat(), preview)
    unknown = (only or set()) - {a.id for a in plan.actions}
    if unknown:
        raise PlanRejected(f"not in the plan: {sorted(unknown)}")
    clients = {}
    for action in plan.actions:
        if only is not None and action.id not in only:
            continue
        check, execute = HANDLERS[action.type]
        ec2 = clients.setdefault(action.region, session.client("ec2", region_name=action.region))
        reason = check(ec2, action)
        if reason:
            report.outcomes.append(Outcome(action.id, "skipped", reason))
            continue
        if preview:
            report.outcomes.append(Outcome(action.id, "would_apply"))
            continue
        try:
            execute(ec2, action)
            report.outcomes.append(Outcome(action.id, "applied"))
        except ClientError as e:
            report.outcomes.append(Outcome(action.id, "failed", _code(e)))
    return report
