from fastapi import APIRouter, Query
from tools.db_tools import (
    _mock_wafer_map, _mock_lot_trend_full,
    _mock_defect_map, _mock_defect_review,
    _mock_defect_trend_full, _mock_yield_defect,
    _mock_defect_yield_history, _mock_defect_step_overlay,
)

router = APIRouter(prefix="/api/chart", tags=["chart"])


@router.get("/wafer-map")
def wafer_map(lot_id: str = Query(...)):
    return _mock_wafer_map(lot_id)


@router.get("/trend")
def trend(lot_id: str = Query(...), metric: str = Query("thickness")):
    return _mock_lot_trend_full(lot_id, metric)


@router.get("/defect-map")
def defect_map(lot_id: str = Query(...), wafer_no: int = Query(...)):
    return _mock_defect_map(lot_id, wafer_no)


@router.get("/defect-review")
def defect_review(lot_id: str = Query(...), wafer_no: int = Query(...), defect_id: str = Query(...)):
    return _mock_defect_review(lot_id, wafer_no, defect_id)


@router.get("/defect-trend")
def defect_trend(lot_id: str = Query(...), defect_type: str = Query(...)):
    return _mock_defect_trend_full(lot_id, defect_type)


@router.get("/yield-defect")
def yield_defect(lot_id: str = Query(...), wafer_no: int = Query(...)):
    return _mock_yield_defect(lot_id, wafer_no)


@router.get("/defect-yield-history")
def defect_yield_history(lot_id: str = Query(...), defect_type: str = Query(...)):
    return _mock_defect_yield_history(lot_id, defect_type)


@router.get("/defect-step-overlay")
def defect_step_overlay(lot_id: str = Query(...), wafer_no: int = Query(...)):
    return _mock_defect_step_overlay(lot_id, wafer_no)
