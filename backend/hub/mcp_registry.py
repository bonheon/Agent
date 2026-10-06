"""
MCP 서버 레지스트리 — mcp_servers.yaml 의 서버들에서 tool 을 받아온다.

서버마다 따로 받아오므로 한 서버가 죽어도 나머지는 살아 있고,
죽은 서버의 tool 은 목록에서 빠져 routing 단계에서 "unavailable" 로 처리된다.
받아온 tool 은 langchain BaseTool 이라 bind_tools / ToolNode 에 그대로 들어간다
(호출 시 adapter 가 MCP call_tool 을 대신 보낸다).
"""
import asyncio
import logging
import os
import re
from pathlib import Path
from typing import Any

import yaml
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from hub.store import now_iso

log = logging.getLogger("mcp")

CONFIG_PATH = Path(__file__).resolve().parent.parent / "mcp_servers.yaml"
LOAD_TIMEOUT_S = float(os.getenv("MCP_LOAD_TIMEOUT_SEC", "10"))

_ENV_RE = re.compile(r"\$\{(\w+)(?::-([^}]*))?\}")


def _expand(value: Any) -> Any:
    """${VAR} / ${VAR:-default} 치환 (문자열 · dict · list 재귀)."""
    if isinstance(value, str):
        return _ENV_RE.sub(lambda m: os.getenv(m.group(1)) or (m.group(2) or ""), value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def load_config() -> dict[str, dict]:
    """활성화된 서버만 {name: connection} 로. enabled 는 yaml 에서 빼고 넘긴다."""
    raw = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    servers = {}
    for name, conf in (raw.get("servers") or {}).items():
        conf = _expand(conf)
        if str(conf.pop("enabled", True)).lower() not in ("true", "1", "yes"):
            continue
        servers[name] = conf
    return servers


# 마지막으로 받아온 결과 — status 는 /api/hub/meta 로 화면에 노출
_status: dict[str, dict] = {}


def _root_cause(e: BaseException) -> BaseException:
    """anyio TaskGroup 이 감싼 ExceptionGroup 에서 실제 원인(연결 거부 등)을 꺼낸다."""
    while getattr(e, "exceptions", None):
        e = e.exceptions[0]
    return e


async def _load_one(client: MultiServerMCPClient, name: str) -> list[BaseTool]:
    return await asyncio.wait_for(client.get_tools(server_name=name), LOAD_TIMEOUT_S)


async def load_tools() -> dict[str, BaseTool]:
    """모든 서버에서 tool 을 받아 {tool 이름: tool}. 이름이 겹치면 yaml 에서 먼저 적힌 서버가 이긴다."""
    servers = load_config()
    client = MultiServerMCPClient(servers)
    names = list(servers)
    results = await asyncio.gather(*(_load_one(client, n) for n in names), return_exceptions=True)

    tools: dict[str, BaseTool] = {}
    status: dict[str, dict] = {}
    for name, res in zip(names, results):
        url = servers[name].get("url") or servers[name].get("command", "")
        if isinstance(res, BaseException):
            cause = _root_cause(res)
            err = "timeout" if isinstance(cause, asyncio.TimeoutError) else f"{type(cause).__name__}: {cause}"
            log.warning("MCP '%s' (%s) 연결 실패 — %s", name, url, err[:200])
            status[name] = {"name": name, "url": url, "status": "down", "tools": [], "error": err[:300], "checked_at": now_iso()}
            continue
        mine = []
        for t in res:
            if t.name in tools:
                log.warning("tool '%s' 가 여러 MCP 서버에 있음 — '%s' 것은 무시", t.name, name)
                continue
            tools[t.name] = t
            mine.append(t.name)
        status[name] = {"name": name, "url": url, "status": "ok", "tools": mine, "error": None, "checked_at": now_iso()}

    _status.clear()
    _status.update(status)
    return tools


def status() -> list[dict]:
    return list(_status.values())
