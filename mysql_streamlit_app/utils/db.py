"""MySQL 접속과 query() 하나. 각 페이지(views/*.py)의 데이터 함수가 SQL 과 값을 넘겨 DataFrame 을 받는다.

- 비밀번호는 환경 변수 DB_PASSWORD 로만 받는다(샘플처럼 코드에 적지 않는다).
- 접속 값: DB_HOST·DB_PORT·DB_USER·DB_NAME (없으면 127.0.0.1·3306·root·mysql_streamlit_app). 팀 .env.example 과 같은 이름이다.
- SQL 의 값 자리는 %s 다. 샘플의 f-문자열과 달리 값에 따옴표가 들어가도 SQL 이 깨지지 않는다.
  값을 넘기는 SQL 안에서 글자 % 를 쓰려면 %% 로 적는다.
"""
import os

import mysql.connector
import pandas as pd
import streamlit as st

from utils.constants import DB_NAME


def _connect():
    pwd = os.environ.get("DB_PASSWORD")
    if not pwd:
        st.error("MySQL 비밀번호가 없습니다. 터미널에서 $env:DB_PASSWORD='비밀번호' 를 넣고 streamlit run app.py 를 다시 실행하세요.")
        st.stop()
    try:
        return mysql.connector.connect(
            host=os.environ.get("DB_HOST", "127.0.0.1"),
            port=int(os.environ.get("DB_PORT") or 3306),
            user=os.environ.get("DB_USER", "root"),
            password=pwd,
            database=os.environ.get("DB_NAME", DB_NAME),
            charset="utf8mb4",
        )
    except mysql.connector.Error as e:
        st.error(
            "MySQL 에 접속하지 못했다. MySQL 서비스가 켜져 있는지, 비밀번호(DB_PASSWORD)가 맞는지, "
            f"database\\build_db.py 로 {DB_NAME} 을 만들었는지 확인해라.\n\n{e}"
        )
        st.stop()


# ponytail: 결과는 앱을 다시 켤 때까지 캐시된다. DB 를 고친 뒤에는 앱을 다시 켜거나 오른쪽 위 메뉴 › Clear cache.
# 쿼리마다 접속을 새로 연다. 혼자 쓰는 로컬 앱이라 충분하고, 여러 사람이 쓰면 st.cache_resource 로 연결을 묶는다.
@st.cache_data(show_spinner=False)
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description]
        df = pd.DataFrame(cur.fetchall(), columns=cols)
    finally:
        conn.close()
    # 값이 모두 NULL 인 열은 object 로 와서 빼기 같은 계산이 안 된다. 숫자 열(NaN)로 맞춘다.
    for col in df.columns:
        if df[col].isna().all():
            df[col] = df[col].astype(float)
    return df
