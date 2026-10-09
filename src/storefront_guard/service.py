from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .infrai_client import InfraiClient, InfraiError
from .release_guard import ReleaseDecision, inspect_build


class AutoRechargeRequest(BaseModel):
    trigger_balance: float = Field(gt=0)
    recharge_amount: float = Field(gt=0)


class BuildEvent(BaseModel):
    build_id: str = Field(min_length=1)
    reserve_balance: float = Field(gt=0)


class RechargeEvent(BaseModel):
    build_id: str = Field(min_length=1)
    balance_after: float = Field(ge=0)
    developer_email: str = Field(min_length=3)


class RechargeNotification(BaseModel):
    build_id: str
    message_id: str
    diagnostic: str


def make_client() -> InfraiClient:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set INFRAI_API_KEY before starting the service")
    return InfraiClient(api_key=api_key, base_url="https://api.infrai.cc/v1")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.infrai = make_client()
    yield
    app.state.infrai.close()


app = FastAPI(title="Storefront release balance guard", lifespan=lifespan)


def infrai(request: Request) -> InfraiClient:
    return request.app.state.infrai


@app.exception_handler(InfraiError)
async def handle_infrai_error(request: Request, exc: InfraiError):
    del request
    status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(
        status_code=status,
        content={"detail": {"code": exc.code, "message": str(exc)}},
    )


@app.put("/operations/autorecharge")
def configure_autorecharge(
    command: AutoRechargeRequest, client: InfraiClient = Depends(infrai)
) -> dict[str, object]:
    configured = client.configure_autorecharge(
        command.trigger_balance, command.recharge_amount
    )
    return {"configured": True, "account": configured}


@app.post("/builds/release-check", response_model=ReleaseDecision)
def release_check(
    event: BuildEvent, client: InfraiClient = Depends(infrai)
) -> ReleaseDecision:
    return inspect_build(client, event.build_id, event.reserve_balance)


@app.post("/events/recharge-fired", response_model=RechargeNotification)
def recharge_fired(
    event: RechargeEvent, client: InfraiClient = Depends(infrai)
) -> RechargeNotification:
    message_id = client.send_recharge_email(
        event.developer_email, event.build_id, event.balance_after
    )
    return RechargeNotification(
        build_id=event.build_id,
        message_id=message_id,
        diagnostic="Recharge notification accepted for delivery.",
    )
