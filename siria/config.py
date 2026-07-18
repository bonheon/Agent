"""전역 설정.

내부망 정보(DB, Milvus, LLM 엔드포인트)는 전부 환경변수로 주입한다.
.env 파일을 쓰려면 python-dotenv 로 로드하거나 셸에서 export 한다.
"""
import os
from functools import lru_cache


class Settings:
    # --- LLM (OpenAI 호환 API 기준) ---
    # TODO: 내부망 LLM 엔드포인트/모델명 채우기
    llm_base_url: str = os.getenv("SIRIA_LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("SIRIA_LLM_API_KEY", "EMPTY")
    llm_model: str = os.getenv("SIRIA_LLM_MODEL", "")
    llm_temperature: float = float(os.getenv("SIRIA_LLM_TEMPERATURE", "0"))

    # --- DB ---
    # TODO: 내부망 DB 접속 정보 채우기 (예: oracle/postgres DSN)
    db_dsn: str = os.getenv("SIRIA_DB_DSN", "")

    # --- Milvus (RAG) ---
    # TODO: 내부망 Milvus 주소/컬렉션명 채우기
    milvus_uri: str = os.getenv("SIRIA_MILVUS_URI", "")
    milvus_collection: str = os.getenv("SIRIA_MILVUS_COLLECTION", "fab_knowledge")

    # --- Observability (Phoenix/Arize) ---
    # true 로 켜면 app 기동 시 tracing 이 활성화된다. (observability.py 참고)
    phoenix_enabled: bool = os.getenv("SIRIA_PHOENIX_ENABLED", "false").lower() == "true"
    # TODO: 내부망 Phoenix collector 주소 채우기
    phoenix_endpoint: str = os.getenv("SIRIA_PHOENIX_ENDPOINT", "http://localhost:6006")

    # --- Agent 기본값 ---
    default_recursion_limit: int = int(os.getenv("SIRIA_RECURSION_LIMIT", "15"))


settings = Settings()


@lru_cache
def get_llm():
    """agent factory 가 사용할 기본 LLM 인스턴스.

    내부망 OpenAI 호환 엔드포인트(vLLM 등)를 가정한다.
    """
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        temperature=settings.llm_temperature,
    )
