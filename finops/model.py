"""Findings, actions and plans.

A finding is something worth a human's attention. Some findings carry an
action the tool can take; the rest are report-only because the safe fix
needs context the tool doesn't have (deleting a volume loses data, stopping
a database breaks whoever still uses it).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

PLAN_TTL = timedelta(days=7)
KEEP_TAG = "finops:keep"


def now() -> datetime:
    return datetime.now(timezone.utc)


def tags_of(resource: dict) -> dict[str, str]:
    return {t["Key"]: t["Value"] for t in resource.get("Tags", []) or []}


def is_kept(resource: dict) -> bool:
    return tags_of(resource).get(KEEP_TAG, "").lower() == "true"


@dataclass
class Action:
    type: str            # modify_volume | delete_snapshot | release_address
    region: str
    resource_id: str
    params: dict = field(default_factory=dict)
    id: str = ""

    def __post_init__(self):
        if not self.id:
            self.id = f"{self.type}:{self.region}:{self.resource_id}"


@dataclass
class Finding:
    check: str
    region: str
    resource_id: str
    summary: str
    monthly_saving_usd: float | None = None   # None = can't estimate honestly
    action: Action | None = None
    detail: dict = field(default_factory=dict)


@dataclass
class Plan:
    account_id: str
    regions: list[str]
    findings: list[Finding]
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: now().isoformat())
    expires_at: str = field(default_factory=lambda: (now() + PLAN_TTL).isoformat())
    notes: list[str] = field(default_factory=list)

    @property
    def actions(self) -> list[Action]:
        return [f.action for f in self.findings if f.action]

    def total_saving(self, actionable_only: bool = False) -> float:
        return round(sum(f.monthly_saving_usd or 0 for f in self.findings
                         if f.action or not actionable_only), 2)

    def expired(self, at: datetime | None = None) -> bool:
        return (at or now()) > datetime.fromisoformat(self.expires_at)

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2, sort_keys=True, default=str)

    def digest(self) -> str:
        """Fingerprint of the plan, recorded with every approval."""
        return hashlib.sha256(self.to_json().encode()).hexdigest()[:16]

    @classmethod
    def from_json(cls, text: str) -> Plan:
        raw = json.loads(text)
        findings = []
        for f in raw.pop("findings"):
            action = Action(**f.pop("action")) if f.get("action") else None
            f.pop("action", None)
            findings.append(Finding(**f, action=action))
        return cls(findings=findings, **raw)
