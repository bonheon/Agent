"""사내 지식베이스(Milvus) RAG 검색 로직.

순수 파이썬 — 프레임워크 의존 없음.
"""
from core.errors import ToolError

# TODO: mock 제거하고 Milvus 검색으로 교체
#   - 접속: config.settings.milvus_uri / milvus_collection
#   - embedding 모델 호출 → pymilvus search → 상위 top_k 반환
_MOCK_DOCS = [
    {
        "title": "Photo 공정 CD OOC 대응 절차",
        "source": "fab-manual/photo/spc-003",
        "content": "CD 측정치가 관리 상한을 초과하면 해당 Lot 을 Hold 하고 "
        "계측 재측정을 1회 수행한다. 재측정도 OOC 이면 공정 엔지니어에게 "
        "이관하고 동일 레시피 후속 Lot 진행을 중단한다.",
        "score": 0.91,
    },
    {
        "title": "Etch 설비 알람 E-4402 트러블슈팅",
        "source": "fab-manual/etch/alarm-e4402",
        "content": "E-4402 는 챔버 압력 이상 알람이다. 1) 진공 라인 리크 체크 "
        "2) 스로틀 밸브 동작 확인 3) 재발 시 PM 요청.",
        "score": 0.84,
    },
    {
        "title": "Lot Hold 해제 프로세스",
        "source": "fab-manual/common/hold-release",
        "content": "Hold 해제는 Hold 를 건 부서의 승인 후 MES 에서 해제한다. "
        "품질 Hold 는 QA 승인이 추가로 필요하다.",
        "score": 0.78,
    },
]


def search(query: str, top_k: int = 3) -> list[dict]:
    """지식베이스에서 query 와 의미적으로 유사한 문서 top_k 개를 반환한다."""
    if not query.strip():
        raise ToolError("조회 실패: 검색어가 비어 있습니다. 질문 내용을 검색어로 전달하세요.")
    return _MOCK_DOCS[:top_k]
