from fastapi import APIRouter, Query
from tools.wip_tools import get_wip_status, list_supported_areas

router = APIRouter(prefix="/api/wip", tags=["wip"])


@router.get("/status")
def wip_status(area: str = Query(..., description="Area 키 (예: M14 CMP)")):
    return get_wip_status(area)


@router.get("/areas")
def wip_areas():
    return {"areas": list_supported_areas()}
