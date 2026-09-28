"""Command line.

  finops scan  --region us-east-1 --region eu-west-2 [--profile p] [--out plan.json]
  finops apply plan.json --approved-by "Jane Doe" [--only <action-id> ...] [--preview] [--yes]

`scan` only needs read access. `apply` shows the plan digest and asks for
confirmation unless --yes is given.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import boto3

from .apply import PlanRejected, apply_plan
from .checks import Config
from .model import Plan
from .scan import render, scan


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="finops", description="Find AWS waste; fix it only after approval.")
    p.add_argument("--profile")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan", help="read-only scan; writes a plan")
    s.add_argument("--region", action="append", required=True)
    s.add_argument("--out", default="plan.json")
    s.add_argument("--snapshot-min-age-days", type=int, default=30)
    s.add_argument("--idle-window-days", type=int, default=14)
    a = sub.add_parser("apply", help="apply an approved plan")
    a.add_argument("plan")
    a.add_argument("--approved-by", required=True)
    a.add_argument("--only", action="append", help="action ID to apply (repeatable); default: all")
    a.add_argument("--preview", action="store_true", help="re-check everything, change nothing")
    a.add_argument("--yes", action="store_true", help="skip the confirmation prompt")
    args = p.parse_args(argv)
    session = boto3.Session(profile_name=args.profile)

    if args.cmd == "scan":
        plan = scan(session, args.region, Config(snapshot_min_age_days=args.snapshot_min_age_days,
                                                 idle_window_days=args.idle_window_days))
        Path(args.out).write_text(plan.to_json())
        print(render(plan))
        print(f"\nPlan written to {args.out}. Nothing was changed.")
        return 0

    plan = Plan.from_json(Path(args.plan).read_text())
    print(render(plan))
    if not (args.preview or args.yes):
        answer = input(f"\nApply plan {plan.plan_id} (digest {plan.digest()}) as {args.approved_by!r}? "
                       "Type the digest to confirm: ")
        if answer.strip() != plan.digest():
            print("Not confirmed; nothing changed.")
            return 1
    try:
        report = apply_plan(session, plan, args.approved_by, only=set(args.only) if args.only else None,
                            preview=args.preview)
    except PlanRejected as e:
        print(f"Rejected: {e}", file=sys.stderr)
        return 2
    for o in report.outcomes:
        print(f"{o.status:<12} {o.action_id}  {o.reason}")
    return 0 if report.count("failed") == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
