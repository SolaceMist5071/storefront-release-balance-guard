from storefront_guard.release_guard import ReleaseState, assess_release


def test_checkout_release_waits_when_balance_reaches_reserve() -> None:
    decision = assess_release(
        build_id="storefront-1842",
        balance_data={"balance": 4.75},
        reserve_balance=5.0,
    )

    assert decision.state is ReleaseState.WAITING_FOR_RECHARGE
    assert decision.observed_balance == 4.75
    assert "storefront-1842" in decision.diagnostic


def test_checkout_release_is_ready_above_reserve() -> None:
    decision = assess_release(
        build_id="storefront-1843",
        balance_data={"balance": 8.25},
        reserve_balance=5.0,
    )

    assert decision.state is ReleaseState.READY
