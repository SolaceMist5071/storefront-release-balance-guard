import httpx

from storefront_guard.infrai_client import InfraiClient


def test_balance_retries_after_rate_limit_and_reads_envelope() -> None:
    calls = 0
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.method == "GET"
        assert request.url.path == "/v1/account/balance"
        assert request.content == b""
        if calls == 1:
            return httpx.Response(
                429,
                headers={"Retry-After": "0"},
                json={"ok": False, "data": None, "error": {"code": ""}},
            )
        return httpx.Response(
            200,
            json={"ok": True, "data": {"balance": 12.0}, "error": None},
        )

    client = InfraiClient(
        api_key="test-key",
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
    )
    try:
        assert client.balance() == {"balance": 12.0}
    finally:
        client.close()

    assert calls == 2
    assert sleeps == [0.0]
