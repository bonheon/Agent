from fastapi import APIRouter, Query

from hub.mcp_data import call

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/daily")
async def daily_report(
    area: str = Query(..., description="Area 키 (예: M14 CMP)"),
    date: str | None = Query(None, description="YYYY-MM-DD, 생략 시 전일"),
):
    return await call("ui_daily_report", area_key=area, report_date=date)
