"""MCP 서버 어댑터 — 스텁.

핵심 아이디어: LangGraph tool 과 똑같이 core/ 의 서비스 함수를 그대로 호출한다.
비즈니스 로직은 core/ 에만 있으므로 어댑터 계층에서 로직 중복이 없다.

TODO: 실제 도입 시
  1. pip install "mcp[cli]"
  2. 아래 스텁을 참고해 노출할 core 함수를 @mcp.tool() 로 감싼다.
  3. 실행: python -m adapters.mcp_server
"""
# from mcp.server.fastmcp import FastMCP
#
# from core import lot_service
#
# mcp = FastMCP("siria")
#
#
# @mcp.tool()
# def get_lot_info(lot_id: str) -> dict:
#     """Lot 번호 1개의 현재 상태를 조회한다."""
#     return lot_service.get_lot_info(lot_id)
#
#
# if __name__ == "__main__":
#     mcp.run()
