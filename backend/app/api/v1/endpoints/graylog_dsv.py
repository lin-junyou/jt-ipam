"""Graylog DSV 查表（lookup table）整合。

對外提供一個 token 保護的 DSV 端點，Graylog 用「DSV File from HTTP」資料配接器
定時抓取，key=IP、value=主機名稱 / FQDN。功能預設關閉，於管理區開啟並設定路徑。

  GET /api/v1/lookup/{name}?token=<token>   →  text/csv 或 text/tab-separated-values
       192.168.1.10,host-a.example.com
       192.168.1.11,host-b.example.com
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import CurrentUser, require_admin
from app.core.audit import append_audit
from app.core.db import get_session
from app.models.address import IPAddress
from app.schemas.base import StrictModel
from app.services.system_config import get_graylog_dsv, set_graylog_dsv

# 公開（token 保護）— 不掛使用者驗證，給 Graylog 機器抓取
public_router = APIRouter(prefix="/lookup", tags=["lookup"])
# 管理區設定 — admin only
admin_router = APIRouter(prefix="/system", tags=["system"], dependencies=[Depends(require_admin)])


@public_router.get("/{name}")
async def dsv_lookup(
    name: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    token: str = Query("", description="存取權杖"),
) -> PlainTextResponse:
    cfg = await get_graylog_dsv(session)
    if not cfg["enabled"] or name != cfg["path"]:
        raise HTTPException(status_code=404, detail="Not found")
    if not cfg["token"] or token != cfg["token"]:
        raise HTTPException(status_code=401, detail="Invalid token")
    sep = "\t" if cfg["fmt"] == "tsv" else ","
    rows = (await session.execute(
        select(func.host(IPAddress.ip), IPAddress.hostname)
        .where(IPAddress.hostname.is_not(None), IPAddress.hostname != "")
        .order_by(IPAddress.ip)
    )).all()
    lines: list[str] = []
    for ip, host in rows:
        if not ip or not host:
            continue
        h = str(host).strip()
        if sep in h or '"' in h or "\n" in h:  # DSV 安全：含分隔符就跳過
            continue
        lines.append(f"{ip}{sep}{h}")
    media = "text/tab-separated-values" if cfg["fmt"] == "tsv" else "text/csv"
    return PlainTextResponse("\n".join(lines) + ("\n" if lines else ""),
                             media_type=f"{media}; charset=utf-8")


class GraylogDsvOut(StrictModel):
    enabled: bool
    fmt: str
    path: str
    token: str


class GraylogDsvPatch(StrictModel):
    enabled: bool
    fmt: str = "csv"
    path: str = "ip-fqdn"
    regenerate_token: bool = False


@admin_router.get("/graylog-dsv", response_model=GraylogDsvOut)
async def get_graylog_dsv_ep(
    _user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    return await get_graylog_dsv(session)


@admin_router.put("/graylog-dsv", response_model=GraylogDsvOut)
async def put_graylog_dsv_ep(
    payload: GraylogDsvPatch,
    user: CurrentUser,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    out = await set_graylog_dsv(
        session, enabled=payload.enabled, fmt=payload.fmt, path=payload.path,
        regenerate_token=payload.regenerate_token,
        updated_by_user_id=uuid.UUID(str(user.id)),
    )
    await append_audit(
        session, actor_user_id=str(user.id),
        actor_ip=request.client.host if request.client else None,
        actor_user_agent=request.headers.get("user-agent"),
        object_type="system_setting", object_id="graylog_dsv", action="update",
        diff={"enabled": out["enabled"], "fmt": out["fmt"], "path": out["path"]},
    )
    await session.commit()
    return out
