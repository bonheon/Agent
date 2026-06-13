from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers.chat import router as chat_router
from routers.charts import router as charts_router
from routers.yield_analysis import router as yield_router
from routers.wip import router as wip_router
from routers.daily_report import router as report_router

load_dotenv()

app = FastAPI(title="Fab LLM API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(charts_router)
app.include_router(yield_router)
app.include_router(wip_router)
app.include_router(report_router)


@app.get("/health")
def health():
    return {"status": "ok"}
