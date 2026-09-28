"""AWS Lambda entry points.

scan:  scheduled. Writes plans/<id>.json to S3 and emails a summary. Read-only.
apply: invoked by a person with the plan ID and digest from that email.
       Disabled unless the function's ALLOW_APPLY=true.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict

import boto3

from .apply import PlanRejected, apply_plan
from .checks import Config
from .model import Plan
from .scan import render, scan


def _regions(event) -> list[str]:
    raw = (event or {}).get("regions") or os.environ.get("REGIONS") or os.environ.get("AWS_REGION", "us-east-1")
    return [r.strip() for r in (raw if isinstance(raw, list) else raw.split(",")) if r.strip()]


def scan_handler(event, context):
    session = boto3.Session()
    cfg = Config(snapshot_min_age_days=int(os.environ.get("SNAPSHOT_MIN_AGE_DAYS", 30)),
                 idle_window_days=int(os.environ.get("IDLE_WINDOW_DAYS", 14)))
    plan = scan(session, _regions(event), cfg)
    bucket = os.environ["PLAN_BUCKET"]
    session.client("s3").put_object(Bucket=bucket, Key=f"plans/{plan.plan_id}.json",
                                    Body=plan.to_json().encode(), ContentType="application/json")
    summary = {
        "plan_id": plan.plan_id,
        "plan_digest": plan.digest(),
        "findings": len(plan.findings),
        "approvable_actions": len(plan.actions),
        "estimated_monthly_saving_usd": plan.total_saving(actionable_only=True),
    }
    topic = os.environ.get("TOPIC_ARN")
    if topic:
        how = (f'To apply, invoke the apply function with {{"plan_id": "{plan.plan_id}", '
               f'"plan_digest": "{plan.digest()}", "approved_by": "<your name>"}}.')
        session.client("sns").publish(
            TopicArn=topic, Subject=f"FinOps plan {plan.plan_id}: "
                                    f"${summary['estimated_monthly_saving_usd']:,.0f}/month",
            Message=render(plan) + "\n\n" + how)
    return summary


def apply_handler(event, context):
    if os.environ.get("ALLOW_APPLY", "false").lower() != "true":
        return {"status": "disabled", "reason": "set ALLOW_APPLY=true on this function to enable applying plans"}
    for key in ("plan_id", "plan_digest", "approved_by"):
        if not (event or {}).get(key):
            return {"status": "rejected", "reason": f"missing {key}"}
    if not re.fullmatch(r"[0-9a-f]{12}", str(event["plan_id"])):
        return {"status": "rejected", "reason": "malformed plan_id"}
    session = boto3.Session()
    s3 = session.client("s3")
    bucket = os.environ["PLAN_BUCKET"]
    plan = Plan.from_json(s3.get_object(Bucket=bucket, Key=f"plans/{event['plan_id']}.json")["Body"].read())
    try:
        report = apply_plan(session, plan, event["approved_by"], expected_digest=event["plan_digest"],
                            only=set(event["action_ids"]) if event.get("action_ids") else None,
                            preview=bool(event.get("preview")))
    except PlanRejected as e:
        return {"status": "rejected", "reason": str(e)}
    body = json.dumps(asdict(report), indent=2)
    s3.put_object(Bucket=bucket, Key=f"results/{plan.plan_id}-{report.approved_at}.json",
                  Body=body.encode(), ContentType="application/json")
    return {"status": "ok", "applied": report.count("applied"), "would_apply": report.count("would_apply"),
            "skipped": report.count("skipped"), "failed": report.count("failed")}
