"""List prices used for savings estimates.

These are AWS on-demand list prices for us-east-1 in USD. Other regions and
negotiated discounts differ, so every figure the tool prints is an estimate.
Override with `Prices(...)` to match your region or contract.
"""

from __future__ import annotations

from dataclasses import dataclass

HOURS_PER_MONTH = 730


@dataclass(frozen=True)
class Prices:
    ebs_gb_month: dict[str, float] = None  # type: ignore[assignment]
    gp3_iops_month: float = 0.005        # per provisioned IOPS above 3,000
    gp3_mibps_month: float = 0.04        # per MiB/s above 125
    snapshot_gb_month: float = 0.05      # standard tier
    public_ipv4_hour: float = 0.005
    alb_hour: float = 0.0225
    nlb_hour: float = 0.0225

    def __post_init__(self):
        if self.ebs_gb_month is None:
            object.__setattr__(self, "ebs_gb_month", {
                "gp2": 0.10, "gp3": 0.08, "io1": 0.125, "io2": 0.125,
                "st1": 0.045, "sc1": 0.015, "standard": 0.05,
            })

    def volume_month(self, volume_type: str, size_gb: int, iops: int = 0, throughput: int = 0) -> float:
        cost = size_gb * self.ebs_gb_month.get(volume_type, self.ebs_gb_month["gp2"])
        if volume_type == "gp3":
            cost += max(0, iops - 3000) * self.gp3_iops_month
            cost += max(0, throughput - 125) * self.gp3_mibps_month
        return cost


DEFAULT_PRICES = Prices()
