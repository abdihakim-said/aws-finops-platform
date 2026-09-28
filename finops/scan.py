"""Run the checks and build a plan. Nothing here changes any resource."""

from __future__ import annotations

from botocore.exceptions import BotoCoreError, ClientError

from .checks import ALL_CHECKS, Config
from .model import Plan
from .prices import DEFAULT_PRICES, Prices

DEFAULT_CONFIG = Config()


def scan(session, regions: list[str], cfg: Config = DEFAULT_CONFIG, prices: Prices = DEFAULT_PRICES,
         checks=ALL_CHECKS) -> Plan:
    account = session.client("sts").get_caller_identity()["Account"]
    findings, notes = [], []
    for region in regions:
        for check in checks:
            try:
                findings.extend(check(session, region, cfg, prices))
            except ClientError as e:
                code = e.response["Error"]["Code"]
                if code == "OptInRequiredException":
                    notes.append(f"{region}: {check.__name__} skipped (AWS Compute Optimizer is not enabled)")
                else:
                    notes.append(f"{region}: {check.__name__} skipped ({code})")
            except (BotoCoreError, NotImplementedError) as e:
                notes.append(f"{region}: {check.__name__} skipped ({type(e).__name__})")
    findings.sort(key=lambda f: (f.action is None, -(f.monthly_saving_usd or 0), f.check, f.resource_id))
    return Plan(account_id=account, regions=list(regions), findings=findings, notes=notes)


def render(plan: Plan) -> str:
    lines = [
        f"Plan {plan.plan_id} (digest {plan.digest()}) for account {plan.account_id}, "
        f"regions {', '.join(plan.regions)}; expires {plan.expires_at[:16]}Z",
        "",
    ]
    actionable = [f for f in plan.findings if f.action]
    report = [f for f in plan.findings if not f.action]
    for title, rows in (("Can be applied after approval", actionable), ("Report only (needs a human)", report)):
        lines.append(f"{title}: {len(rows)}")
        for f in rows:
            saving = f"${f.monthly_saving_usd:>9,.2f}/mo" if f.monthly_saving_usd is not None else "        n/a   "
            lines.append(f"  {saving}  {f.check:<20} {f.region:<11} {f.resource_id}")
            lines.append(f"  {'':14}  {f.summary}")
        lines.append("")
    lines.append(f"Estimated saving: ${plan.total_saving(actionable_only=True):,.2f}/month from approvable "
                 f"actions, ${plan.total_saving():,.2f}/month including report-only findings "
                 "(us-east-1 list prices).")
    for note in plan.notes:
        lines.append(f"Note: {note}")
    return "\n".join(lines)
