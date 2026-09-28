"""Waste checks. Each one is read-only and returns findings.

Every check is conservative: when in doubt it skips the resource or makes
the finding report-only. A missed saving costs a little money; a wrong
deletion costs a lot more.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from botocore.exceptions import ClientError

from .model import Action, Finding, is_kept, now, tags_of
from .prices import HOURS_PER_MONTH, Prices

# Snapshot tags set by services that manage their own retention.
MANAGED_SNAPSHOT_TAGS = ("aws:backup:source-resource", "aws:dlm:lifecycle-policy-id")
# Copied or imported snapshots carry this placeholder volume ID.
PLACEHOLDER_VOLUME = "vol-ffffffff"


@dataclass(frozen=True)
class Config:
    snapshot_min_age_days: int = 30
    volume_min_age_days: int = 7
    idle_window_days: int = 14
    multipart_min_age_days: int = 7
    # A resource younger than this is never called idle. Defaults to the idle window.
    min_resource_age_days: int | None = None

    @property
    def min_age(self) -> int:
        return self.idle_window_days if self.min_resource_age_days is None else self.min_resource_age_days


def _paginate(client, op: str, key: str, **kwargs):
    for page in client.get_paginator(op).paginate(**kwargs):
        yield from page.get(key, [])


# ---- EBS: gp2 -> gp3 -------------------------------------------------------

def gp3_equivalent(size_gb: int) -> tuple[int, int]:
    """IOPS and throughput a gp3 volume needs to match a gp2 volume's baseline.

    gp2 scales IOPS with size (3/GB, 100 to 16,000) and gives volumes over
    170 GiB up to 250 MiB/s. A plain gp3 conversion gets 3,000 IOPS and
    125 MiB/s, which is slower for large volumes, so provision the difference.
    """
    gp2_iops = min(max(100, 3 * size_gb), 16000)
    return max(3000, gp2_iops), (125 if size_gb <= 170 else 250)


def gp2_volumes(session, region: str, cfg: Config, prices: Prices) -> list[Finding]:
    ec2 = session.client("ec2", region_name=region)
    busy = set()
    try:
        for m in _paginate(ec2, "describe_volumes_modifications", "VolumesModifications",
                           Filters=[{"Name": "modification-state", "Values": ["modifying", "optimizing"]}]):
            busy.add(m["VolumeId"])
    except ClientError:
        pass  # if we can't tell, the modify call will fail safely later
    findings = []
    for v in _paginate(ec2, "describe_volumes", "Volumes",
                       Filters=[{"Name": "volume-type", "Values": ["gp2"]}]):
        # Unattached volumes are reported for deletion instead; converting them saves nothing useful.
        if is_kept(v) or v["VolumeId"] in busy or v["State"] != "in-use":
            continue
        iops, throughput = gp3_equivalent(v["Size"])
        saving = prices.volume_month("gp2", v["Size"]) - prices.volume_month("gp3", v["Size"], iops, throughput)
        if saving <= 0:
            continue
        findings.append(Finding(
            check="gp2_volume", region=region, resource_id=v["VolumeId"],
            summary=f"{v['Size']} GiB gp2 -> gp3 at {iops} IOPS / {throughput} MiB/s (same or better performance)",
            monthly_saving_usd=round(saving, 2),
            action=Action("modify_volume", region, v["VolumeId"],
                          {"VolumeType": "gp3", "Iops": iops, "Throughput": throughput}),
        ))
    return findings


# ---- EBS snapshots ---------------------------------------------------------

def orphaned_snapshots(session, region: str, cfg: Config, prices: Prices) -> list[Finding]:
    ec2 = session.client("ec2", region_name=region)
    existing_volumes = {v["VolumeId"] for v in _paginate(ec2, "describe_volumes", "Volumes")}
    ami_snapshots = {
        m["Ebs"]["SnapshotId"]
        for image in _paginate(ec2, "describe_images", "Images", Owners=["self"])
        for m in image.get("BlockDeviceMappings", []) if "SnapshotId" in m.get("Ebs", {})
    }
    cutoff = now() - timedelta(days=cfg.snapshot_min_age_days)
    findings = []
    for s in _paginate(ec2, "describe_snapshots", "Snapshots", OwnerIds=["self"]):
        tags = tags_of(s)
        if (s["State"] != "completed" or s["StartTime"] > cutoff or is_kept(s)
                or s["SnapshotId"] in ami_snapshots
                or any(t in tags for t in MANAGED_SNAPSHOT_TAGS)
                or s.get("VolumeId", PLACEHOLDER_VOLUME) == PLACEHOLDER_VOLUME
                or s.get("VolumeId") in existing_volumes):
            continue
        upper = s.get("VolumeSize", 0) * prices.snapshot_gb_month
        findings.append(Finding(
            check="orphaned_snapshot", region=region, resource_id=s["SnapshotId"],
            summary=(f"Source volume {s['VolumeId']} no longer exists; not used by an AMI, "
                     f"AWS Backup or DLM; up to ${upper:.2f}/month (snapshots are incremental)"),
            monthly_saving_usd=None,  # the billed size of an incremental snapshot isn't exposed
            action=Action("delete_snapshot", region, s["SnapshotId"]),
            detail={"upper_bound_usd": round(upper, 2), "volume_size_gb": s.get("VolumeSize")},
        ))
    return findings


# ---- Elastic IPs -----------------------------------------------------------

def unattached_eips(session, region: str, cfg: Config, prices: Prices) -> list[Finding]:
    ec2 = session.client("ec2", region_name=region)
    findings = []
    for a in ec2.describe_addresses().get("Addresses", []):
        if "AssociationId" in a or is_kept(a) or "AllocationId" not in a:
            continue
        findings.append(Finding(
            check="unattached_eip", region=region, resource_id=a["AllocationId"],
            summary=f"Elastic IP {a.get('PublicIp')} is not associated with anything",
            monthly_saving_usd=round(prices.public_ipv4_hour * HOURS_PER_MONTH, 2),
            action=Action("release_address", region, a["AllocationId"]),
        ))
    return findings


# ---- Report-only checks -----------------------------------------------------

def unattached_volumes(session, region: str, cfg: Config, prices: Prices) -> list[Finding]:
    ec2 = session.client("ec2", region_name=region)
    cutoff = now() - timedelta(days=cfg.volume_min_age_days)
    findings = []
    for v in _paginate(ec2, "describe_volumes", "Volumes",
                       Filters=[{"Name": "status", "Values": ["available"]}]):
        if is_kept(v) or v["CreateTime"] > cutoff:
            continue
        cost = prices.volume_month(v["VolumeType"], v["Size"], v.get("Iops", 0), v.get("Throughput", 0))
        findings.append(Finding(
            check="unattached_volume", region=region, resource_id=v["VolumeId"],
            summary=f"{v['Size']} GiB {v['VolumeType']} not attached to any instance. Snapshot it, then delete it",
            monthly_saving_usd=round(cost, 2),
        ))
    return findings


def _metric_sum(cw, namespace: str, metric: str, dimension: dict, days: int, stat: str = "Sum"):
    # Round up to the hour so the current partial day is included.
    end = (now() + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    points = cw.get_metric_statistics(
        Namespace=namespace, MetricName=metric, Dimensions=[dimension],
        StartTime=end - timedelta(days=days), EndTime=end, Period=86400, Statistics=[stat],
    )["Datapoints"]
    return [p[stat] for p in points]


def idle_load_balancers(session, region: str, cfg: Config, prices: Prices) -> list[Finding]:
    elb = session.client("elbv2", region_name=region)
    cw = session.client("cloudwatch", region_name=region)
    cutoff = now() - timedelta(days=cfg.min_age)
    findings = []
    for lb in _paginate(elb, "describe_load_balancers", "LoadBalancers"):
        if lb["CreatedTime"] > cutoff or lb["Type"] not in ("application", "network"):
            continue
        dim = {"Name": "LoadBalancer", "Value": lb["LoadBalancerArn"].split(":loadbalancer/")[1]}
        if lb["Type"] == "application":
            values = _metric_sum(cw, "AWS/ApplicationELB", "RequestCount", dim, cfg.idle_window_days)
            hourly = prices.alb_hour
        else:
            values = _metric_sum(cw, "AWS/NetworkELB", "NewFlowCount", dim, cfg.idle_window_days)
            hourly = prices.nlb_hour
        # Load balancers publish nothing when there is no traffic, so no data means idle.
        if sum(values) == 0:
            findings.append(Finding(
                check="idle_load_balancer", region=region, resource_id=lb["LoadBalancerName"],
                summary=f"{lb['Type']} load balancer with no traffic in {cfg.idle_window_days} days",
                monthly_saving_usd=round(hourly * HOURS_PER_MONTH, 2),
            ))
    return findings


def idle_rds(session, region: str, cfg: Config, prices: Prices) -> list[Finding]:
    rds = session.client("rds", region_name=region)
    cw = session.client("cloudwatch", region_name=region)
    cutoff = now() - timedelta(days=cfg.min_age)
    findings = []
    for db in _paginate(rds, "describe_db_instances", "DBInstances"):
        if db.get("DBInstanceStatus") != "available" or db["InstanceCreateTime"] > cutoff:
            continue
        values = _metric_sum(cw, "AWS/RDS", "DatabaseConnections",
                             {"Name": "DBInstanceIdentifier", "Value": db["DBInstanceIdentifier"]},
                             cfg.idle_window_days, stat="Maximum")
        # RDS always publishes connections, so missing data means we can't tell.
        if values and max(values) == 0:
            findings.append(Finding(
                check="idle_rds", region=region, resource_id=db["DBInstanceIdentifier"],
                summary=(f"{db['DBInstanceClass']} with zero connections in {cfg.idle_window_days} days. "
                         "Confirm with the owner, take a final snapshot, then stop or delete it"),
            ))
    return findings


def ec2_rightsizing(session, region: str, cfg: Config, prices: Prices) -> list[Finding]:
    """Uses AWS Compute Optimizer rather than a home-grown CPU heuristic."""
    co = session.client("compute-optimizer", region_name=region)
    findings = []
    token = None
    while True:
        kwargs = {"nextToken": token} if token else {}
        resp = co.get_ec2_instance_recommendations(**kwargs)
        for rec in resp.get("instanceRecommendations", []):
            if rec.get("finding", "").upper().replace("_", "") != "OVERPROVISIONED":
                continue
            options = sorted(rec.get("recommendationOptions", []), key=lambda o: o.get("rank", 99))
            if not options:
                continue
            best = options[0]
            saving = best.get("savingsOpportunity", {}).get("estimatedMonthlySavings", {}).get("value")
            instance_id = rec["instanceArn"].rsplit("/", 1)[-1]
            findings.append(Finding(
                check="ec2_rightsizing", region=region, resource_id=instance_id,
                summary=(f"{rec['currentInstanceType']} -> {best['instanceType']} "
                         "(Compute Optimizer; needs a stop/start in a maintenance window)"),
                monthly_saving_usd=round(saving, 2) if saving is not None else None,
            ))
        token = resp.get("nextToken")
        if not token:
            return findings


def s3_stale_multipart_uploads(session, region: str, cfg: Config, prices: Prices) -> list[Finding]:
    """Incomplete multipart uploads are billed but invisible in the console."""
    s3 = session.client("s3", region_name=region)
    cutoff = now() - timedelta(days=cfg.multipart_min_age_days)
    findings = []
    for bucket in s3.list_buckets().get("Buckets", []):
        name = bucket["Name"]
        try:
            loc = s3.get_bucket_location(Bucket=name).get("LocationConstraint") or "us-east-1"
            if loc != region:
                continue  # each bucket is checked once, in its own region
            try:
                rules = s3.get_bucket_lifecycle_configuration(Bucket=name).get("Rules", [])
            except ClientError as e:
                if e.response["Error"]["Code"] != "NoSuchLifecycleConfiguration":
                    raise
                rules = []
            if any(r.get("Status") == "Enabled" and "AbortIncompleteMultipartUpload" in r for r in rules):
                continue
            stale = [u for page in s3.get_paginator("list_multipart_uploads").paginate(Bucket=name)
                     for u in page.get("Uploads", []) if u["Initiated"] < cutoff]
        except ClientError:
            continue
        if stale:
            findings.append(Finding(
                check="s3_stale_multipart", region=region, resource_id=name,
                summary=(f"{len(stale)} incomplete multipart uploads older than {cfg.multipart_min_age_days} "
                         "days and no AbortIncompleteMultipartUpload lifecycle rule"),
            ))
    return findings


ACTIONABLE_CHECKS = (gp2_volumes, orphaned_snapshots, unattached_eips)
REPORT_CHECKS = (unattached_volumes, idle_load_balancers, idle_rds, ec2_rightsizing, s3_stale_multipart_uploads)
ALL_CHECKS = ACTIONABLE_CHECKS + REPORT_CHECKS
