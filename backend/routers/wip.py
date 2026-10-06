from fastapi import APIRouter, Query

from hub.mcp_data import call

router = APIRouter(prefix="/api/wip", tags=["wip"])


@router.get("/status")
async def wip_status(area: str = Query(..., description="Area 키 (예: M14 CMP)")):
    return await call("ui_wip_status", area_key=area)


@router.get("/areas")
async def wip_areas():
    return {"areas": await call("ui_wip_areas")}
