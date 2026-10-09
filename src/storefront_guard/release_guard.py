from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from .infrai_client import InfraiClient


class ReleaseState(StrEnum):
    READY = "ready"
    WAITING_FOR_RECHARGE = "waiting_for_recharge"


@dataclass(frozen=True)
class ReleaseDecision:
    build_id: str
    state: ReleaseState
    diagnostic: str
    observed_balance: float


def assess_release(
    build_id: str, balance_data: dict[str, Any], reserve_balance: float
) -> ReleaseDecision:
    observed = float(balance_data["balance"])
    if observed <= reserve_balance:
        return ReleaseDecision(
            build_id=build_id,
            state=ReleaseState.WAITING_FOR_RECHARGE,
            diagnostic=(
                f"Build {build_id} is complete; release is waiting for the "
                f"balance to rise above {reserve_balance:.2f}."
            ),
            observed_balance=observed,
        )
    return ReleaseDecision(
        build_id=build_id,
        state=ReleaseState.READY,
        diagnostic=f"Build {build_id} is complete and its release check passed.",
        observed_balance=observed,
    )


def inspect_build(
    client: InfraiClient, build_id: str, reserve_balance: float
) -> ReleaseDecision:
    return assess_release(build_id, client.balance(), reserve_balance)
