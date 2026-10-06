"""차트 데이터 — MCP 화면 전용 tool(ui_*)을 그대로 중계한다."""
from fastapi import APIRouter, Query

from hub.mcp_data import call

router = APIRouter(prefix="/api/chart", tags=["chart"])


@router.get("/wafer-map")
async def wafer_map(lot_id: str = Query(...)):
    return await call("ui_wafer_map", lot_id=lot_id)


@router.get("/trend")
async def trend(lot_id: str = Query(...), metric: str = Query("thickness")):
    return await call("ui_lot_trend", lot_id=lot_id, metric=metric)


@router.get("/defect-map")
async def defect_map(lot_id: str = Query(...), wafer_no: int = Query(...)):
    return await call("ui_defect_map", lot_id=lot_id, wafer_no=wafer_no)


@router.get("/defect-review")
async def defect_review(lot_id: str = Query(...), wafer_no: int = Query(...), defect_id: str = Query(...)):
    return await call("ui_defect_review", lot_id=lot_id, wafer_no=wafer_no, defect_id=defect_id)


@router.get("/defect-trend")
async def defect_trend(lot_id: str = Query(...), defect_type: str = Query(...)):
    return await call("ui_defect_trend", lot_id=lot_id, defect_type=defect_type)


@router.get("/yield-defect")
async def yield_defect(lot_id: str = Query(...), wafer_no: int = Query(...)):
    return await call("ui_yield_defect", lot_id=lot_id, wafer_no=wafer_no)


@router.get("/defect-yield-history")
async def defect_yield_history(lot_id: str = Query(...), defect_type: str = Query(...)):
    return await call("ui_defect_yield_history", lot_id=lot_id, defect_type=defect_type)


@router.get("/defect-step-overlay")
async def defect_step_overlay(lot_id: str = Query(...), wafer_no: int = Query(...)):
    return await call("ui_defect_step_overlay", lot_id=lot_id, wafer_no=wafer_no)
