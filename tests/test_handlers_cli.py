import json

import pytest
from conftest import attached_volume

from finops import handlers
from finops.cli import main as cli

REGION = "us-east-1"


@pytest.fixture
def deployed(aws, monkeypatch):
    s3, sns, ec2 = aws.client("s3"), aws.client("sns"), aws.client("ec2")
    s3.create_bucket(Bucket="finops-plans")
    topic = sns.create_topic(Name="finops")["TopicArn"]
    monkeypatch.setenv("PLAN_BUCKET", "finops-plans")
    monkeypatch.setenv("TOPIC_ARN", topic)
    monkeypatch.setenv("REGIONS", REGION)
    monkeypatch.setenv("SNAPSHOT_MIN_AGE_DAYS", "0")
    vol = attached_volume(ec2, 100)
    return {"s3": s3, "ec2": ec2, "vol": vol}


def test_scan_handler_stores_the_plan_and_changes_nothing(deployed):
    out = handlers.scan_handler({}, None)
    assert out["approvable_actions"] == 1 and out["estimated_monthly_saving_usd"] == 2.0
    body = deployed["s3"].get_object(Bucket="finops-plans", Key=f"plans/{out['plan_id']}.json")["Body"].read()
    assert json.loads(body)["plan_id"] == out["plan_id"]
    assert deployed["ec2"].describe_volumes(VolumeIds=[deployed["vol"]])["Volumes"][0]["VolumeType"] == "gp2"


def test_apply_handler_is_off_by_default(deployed):
    out = handlers.scan_handler({}, None)
    res = handlers.apply_handler({"plan_id": out["plan_id"], "plan_digest": out["plan_digest"],
                                  "approved_by": "Jane"}, None)
    assert res["status"] == "disabled"


def test_apply_handler_needs_the_digest_the_approver_saw(deployed, monkeypatch):
    monkeypatch.setenv("ALLOW_APPLY", "true")
    out = handlers.scan_handler({}, None)
    missing = handlers.apply_handler({"plan_id": out["plan_id"], "approved_by": "Jane"}, None)
    assert missing["status"] == "rejected"
    bad_id = handlers.apply_handler({"plan_id": "../../secrets", "plan_digest": "x", "approved_by": "Jane"}, None)
    assert bad_id == {"status": "rejected", "reason": "malformed plan_id"}
    assert missing["status"] == "rejected"
    wrong = handlers.apply_handler({"plan_id": out["plan_id"], "plan_digest": "0" * 16,
                                    "approved_by": "Jane"}, None)
    assert wrong["status"] == "rejected"
    ok = handlers.apply_handler({"plan_id": out["plan_id"], "plan_digest": out["plan_digest"],
                                 "approved_by": "Jane"}, None)
    assert ok == {"status": "ok", "applied": 1, "would_apply": 0, "skipped": 0, "failed": 0}
    assert deployed["ec2"].describe_volumes(VolumeIds=[deployed["vol"]])["Volumes"][0]["VolumeType"] == "gp3"
    results = deployed["s3"].list_objects_v2(Bucket="finops-plans", Prefix="results/")["KeyCount"]
    assert results == 1


def test_cli_scan_then_apply(deployed, tmp_path, monkeypatch, capsys):
    plan_file = tmp_path / "plan.json"
    assert cli(["scan", "--region", REGION, "--out", str(plan_file), "--snapshot-min-age-days", "0"]) == 0
    assert "Nothing was changed" in capsys.readouterr().out
    monkeypatch.setattr("builtins.input", lambda _: "wrong-digest")
    assert cli(["apply", str(plan_file), "--approved-by", "Jane"]) == 1
    assert deployed["ec2"].describe_volumes(VolumeIds=[deployed["vol"]])["Volumes"][0]["VolumeType"] == "gp2"
    assert cli(["apply", str(plan_file), "--approved-by", "Jane", "--yes"]) == 0
    assert deployed["ec2"].describe_volumes(VolumeIds=[deployed["vol"]])["Volumes"][0]["VolumeType"] == "gp3"
