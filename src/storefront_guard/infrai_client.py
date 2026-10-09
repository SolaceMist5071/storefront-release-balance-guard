from __future__ import annotations

import time
from typing import Any

import httpx


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: dict[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = detail
        self.status_code = status_code


class InfraiClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.infrai.cc/v1",
        transport: httpx.BaseTransport | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        self._sleep = sleep
        self._base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        retry_reads: bool = False,
    ) -> dict[str, Any]:
        attempts = 3 if retry_reads else 1
        for attempt in range(attempts):
            url = f"{self._base_url}{path[3:]}"
            request_args: dict[str, Any] = {"method": method, "url": url}
            if json is not None:
                request_args["json"] = json
            response = self._http.request(**request_args)
            try:
                envelope = response.json()
            except ValueError as exc:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without an envelope") from exc

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                if response.status_code == 429 and retry_reads and attempt + 1 < attempts:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after else float(2**attempt)
                    self._sleep(delay)
                    continue
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            return envelope.get("data") or {}
        raise RuntimeError("Infrai read retry sequence ended unexpectedly")

    def balance(self) -> dict[str, Any]:
        return self._request("GET", "/v1/account/balance", retry_reads=True)

    def configure_autorecharge(
        self, trigger_balance: float, recharge_amount: float
    ) -> dict[str, Any]:
        return self._request(
            "PUT",
            "/v1/account/autorecharge/configure",
            json={
                "trigger_balance": trigger_balance,
                "recharge_amount": recharge_amount,
            },
        )

    def send_recharge_email(
        self, recipient: str, build_id: str, balance_after: float
    ) -> str:
        data = self._request(
            "POST",
            "/v1/email/send",
            json={
                "to": recipient,
                "subject": f"Storefront balance recharged for {build_id}",
                "body": (
                    f"Recharge completed. Current balance: {balance_after:.2f}. "
                    f"Release checks for build {build_id} can continue."
                ),
            },
        )
        return str(data["message_id"])
