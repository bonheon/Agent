"""지식베이스(RAG) tool — core/knowledge_service 를 호출하는 얇은 wrapper.

RAG 를 항상 실행하지 않고 tool 로 등록해, LLM 이 필요하다고 판단할 때만
검색하게 한다.
"""
from langchain_core.tools import tool

from core import knowledge_service
from tools.common import safe_tool
from tools.registry import register


@tool
@safe_tool
def search_knowledge(query: str, top_k: int = 3) -> str:
    """사내 지식베이스(업무 매뉴얼, 공정 스펙, 트러블슈팅 사례 문서)를 의미 기반으로 검색한다.

    언제 사용: 실시간 현황 데이터가 아니라 문서화된 지식·절차·기준이 필요할 때만
    호출한다. 예: "CD OOC 나면 어떻게 대응해", "E-4402 알람 조치 방법",
    "Hold 해제 절차". 일반 대화나 실시간 조회 질문에는 호출하지 말 것.

    다른 tool 과의 구분:
    - Lot/설비/재공의 '지금 상태'는 get_lot_info, get_eq_status, get_wip_summary
      등 조회 tool 을 사용한다. 이 tool 은 정적 문서만 반환한다.

    Args:
        query: 검색 질의문. 사용자 질문에서 핵심 키워드 중심으로 다듬어 전달.
        top_k: 반환할 문서 수 (기본 3).
    """
    docs = knowledge_service.search(query, top_k=top_k)
    blocks = [
        f"[{i}] {d['title']} (출처: {d['source']}, 유사도: {d['score']:.2f})\n{d['content']}"
        for i, d in enumerate(docs, start=1)
    ]
    return "\n\n".join(blocks) if blocks else "검색 결과가 없습니다. 다른 검색어로 시도해 보세요."


register(search_knowledge)
