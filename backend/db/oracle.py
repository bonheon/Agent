import os
from dotenv import load_dotenv

load_dotenv()

# cx_Oracle 설치 후 실제 Oracle 연결 시 주석 해제
# import cx_Oracle

def get_connection():
    # return cx_Oracle.connect(
    #     user=os.getenv("ORACLE_USER"),
    #     password=os.getenv("ORACLE_PASSWORD"),
    #     dsn=os.getenv("ORACLE_DSN")
    # )
    raise NotImplementedError("Oracle connection not configured yet")


def query(sql: str, params: dict = None):
    """Oracle DB에 쿼리 실행 후 결과를 list[dict]로 반환"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(sql, params or {})
    columns = [col[0].lower() for col in cursor.description]
    rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return rows
