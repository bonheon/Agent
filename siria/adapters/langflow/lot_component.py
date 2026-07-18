"""langflow 커스텀 컴포넌트 어댑터 — 스텁.

MCP 어댑터와 마찬가지로 core/ 서비스 함수를 그대로 호출한다.

TODO: 실제 도입 시 langflow 버전에 맞는 Component API 로 구현.
"""
# from langflow.custom import Component
# from langflow.io import MessageTextInput, Output
# from langflow.schema import Data
#
# from core import lot_service
#
#
# class LotInfoComponent(Component):
#     display_name = "Siria Lot Info"
#     description = "Lot 번호로 현재 상태를 조회합니다."
#
#     inputs = [MessageTextInput(name="lot_id", display_name="Lot 번호")]
#     outputs = [Output(name="lot_info", display_name="Lot 정보", method="run")]
#
#     def run(self) -> Data:
#         return Data(data=lot_service.get_lot_info(self.lot_id))
