"""Phoenix (Arize) tracing 연동.

SIRIA_PHOENIX_ENABLED=true 일 때만 활성화된다. app 기동 시 setup_tracing() 을
한 번 호출하면 이후 모든 LangChain/LangGraph 호출이 자동 계측된다.
"""
import logging

from config import settings

logger = logging.getLogger(__name__)


def setup_tracing() -> None:
    if not settings.phoenix_enabled:
        logger.info("Phoenix tracing 비활성화 (SIRIA_PHOENIX_ENABLED=false)")
        return

    try:
        from openinference.instrumentation.langchain import LangChainInstrumentor
        from phoenix.otel import register as phoenix_register
    except ImportError:
        logger.warning(
            "Phoenix 관련 패키지 미설치 — tracing 을 건너뜁니다. "
            "(pip install arize-phoenix-otel openinference-instrumentation-langchain)"
        )
        return

    # TODO: 내부망 Phoenix collector 주소 확인 (SIRIA_PHOENIX_ENDPOINT)
    #       phoenix_register 의 endpoint 는 OTLP 경로까지 포함해야 할 수 있음
    #       (예: http://<host>:6006/v1/traces)
    tracer_provider = phoenix_register(
        project_name="siria",
        endpoint=settings.phoenix_endpoint,
    )
    LangChainInstrumentor().instrument(tracer_provider=tracer_provider)
    logger.info("Phoenix tracing 활성화: %s", settings.phoenix_endpoint)
