import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from routers.chat import router as chat_router  # noqa: E402
from routers.charts import router as charts_router  # noqa: E402
from routers.yield_analysis import router as yield_router  # noqa: E402
from routers.wip import router as wip_router  # noqa: E402
from routers.daily_report import router as report_router  # noqa: E402
from routers.hub import router as hub_router  # noqa: E402
from hub.service import scheduler_loop  # noqa: E402


@asynccontextmanager
async def lifespan(_: FastAPI):
    # 이벤터 자동 실행은 OpenAI 호출 비용이 드므로 명시적으로 켤 때만 동작
    task = asyncio.create_task(scheduler_loop()) if os.getenv("HUB_SCHEDULER") == "1" else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="Fab LLM API", version="0.2.0", lifespan=lifespan)

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
app.include_router(hub_router)


@app.get("/health")
def health():
    return {"status": "ok"}
