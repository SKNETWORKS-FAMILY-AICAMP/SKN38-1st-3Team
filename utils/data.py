"""MySQL의 부품·국가·거래 표를 읽고 화면용 단위로 변환한다."""
import os
from pathlib import Path

import mysql.connector
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from utils.constants import COUNTRY_CODES
from utils.parts_catalog import ITEMS, PART_NAMES

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


def _query(sql, params=()):
    try:
        secrets = dict(st.secrets.get("mysql", {}))
    except FileNotFoundError:
        secrets = {}
    settings = {
        "host": os.environ.get("DB_HOST") or secrets.get("host", "127.0.0.1"),
        "port": int(os.environ.get("DB_PORT") or secrets.get("port", 3306)),
        "user": os.environ.get("DB_USER") or secrets.get("user", "root"),
        "password": os.environ.get("DB_PASSWORD") or secrets.get("password"),
        "database": os.environ.get("DB_NAME") or secrets.get("database", "mysql_streamlit_app"),
        "connection_timeout": 10,
        "auth_plugin": "mysql_native_password"
    }
    if not settings["password"]:
        st.error("로컬에서는 프로젝트 루트 .env의 DB_PASSWORD를, Streamlit Cloud에서는 [mysql] Secrets를 설정하세요.")
        st.stop()
    try:
        conn = mysql.connector.connect(**settings)
        try:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return pd.DataFrame(cursor.fetchall(), columns=[c[0] for c in cursor.description])
        finally:
            cursor.close()
            conn.close()
    except mysql.connector.Error:
        st.error("MySQL에 연결하거나 조회하지 못했습니다. 접속 정보(.env 또는 [mysql] Secrets), 외부 접속 허용, DB 적재 여부를 확인하세요.")
        st.stop()


@st.cache_data(ttl=300)
def load_parts():
    return _query("SELECT hsCd, hsKor, hsExp FROM parts WHERE hsCd <> %s", ("8708000000",))


@st.cache_data(ttl=300)
def load_stats():
    codes = tuple(COUNTRY_CODES)
    return _query("SELECT statCd, statKor FROM stats WHERE statCd IN (" + ",".join(["%s"] * len(codes)) + ")", codes)


@st.cache_data(ttl=300)
def load_trades():
    codes = tuple(COUNTRY_CODES)
    frame = _query(
        "SELECT year, statCd, hsCd, expDlr, expwgt, impDlr, impwgt, balPayments "
        "FROM trades WHERE hsCd <> %s AND statCd IN (" + ",".join(["%s"] * len(codes)) + ")",
        ("8708000000", *codes),
    )
    if frame.empty:
        st.error("MySQL에 표시할 거래가 없습니다. 데이터 적재 여부를 확인하세요.")
        st.stop()
    for column in ["expDlr", "expwgt", "impDlr", "impwgt", "balPayments"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    return frame


# 3. 화면에서 쓰는 표로 바꾸기
@st.cache_data(ttl=300)
def load_dashboard_data():
    trades_frame = load_trades()
    parts_frame = load_parts()
    stats_frame = load_stats()
    joined = pd.merge(trades_frame, parts_frame, on="hsCd", how="left")
    joined = pd.merge(joined, stats_frame, on="statCd", how="left")

    named_codes = [code for code, name in ITEMS if code != "기타"]
    joined["부품 코드"] = joined["hsCd"].where(
        joined["hsCd"].isin(named_codes),
        "기타",
    )
    joined["부품"] = joined["부품 코드"].map(PART_NAMES)
    joined["나라"] = joined["statKor"]
    joined["월"] = joined["year"]
    year_parts = joined["year"].str.split(".", expand=True)
    joined["k"] = (year_parts[0].astype(int) - 2021) * 12
    joined["k"] += year_parts[1].astype(int) - 1
    joined["수출액"] = joined["expDlr"] / 1_000_000
    joined["수입액"] = joined["impDlr"] / 1_000_000
    joined["수출중량"] = joined["expwgt"] / 1_000
    joined["수입중량"] = joined["impwgt"] / 1_000
    joined["무역수지"] = joined["balPayments"] / 1_000_000
    dashboard_columns = [
        "월",
        "k",
        "부품 코드",
        "부품",
        "나라",
        "수출액",
        "수입액",
        "수출중량",
        "수입중량",
        "무역수지",
    ]
    dashboard_frame = joined[dashboard_columns]
    dashboard_frame = dashboard_frame.groupby(
        [
            "월",
            "k",
            "부품 코드",
            "부품",
            "나라",
        ],
        as_index=False,
        sort=False,
    ).sum()
    return dashboard_frame
