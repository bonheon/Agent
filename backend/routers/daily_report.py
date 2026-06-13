from fastapi import APIRouter, Query
from tools.daily_report_tools import get_daily_report

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/daily")
def daily_report(
    area: str = Query(..., description="Area 키 (예: M14 CMP)"),
    date: str | None = Query(None, description="YYYY-MM-DD, 생략 시 전일"),
):
    return get_daily_report(area, date)
