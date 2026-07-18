"""DB 커넥션 관리.

각 서비스(lot_service 등)는 반드시 get_connection() 을 통해서만 DB 에 접근한다.
"""
from config import settings


def get_connection():
    """DB 커넥션을 반환한다.

    TODO: 내부망 DB 드라이버(oracledb / psycopg 등)로 구현하고 커넥션 풀 적용.
          접속 정보는 config.settings.db_dsn (SIRIA_DB_DSN 환경변수) 사용.
    """
    raise NotImplementedError(f"DB 커넥션 미구현 (dsn 설정 여부: {bool(settings.db_dsn)})")
