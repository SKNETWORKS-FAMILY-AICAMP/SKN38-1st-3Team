"""진입점. 페이지 설정, 왼쪽 메뉴(페이지 선택), 각 페이지의 그리는 함수(show_…) 호출만 한다.

데이터는 이 PC 의 MySQL(mysql_streamlit_app)에서 읽는다. 실행 전에 README 의 「DB 만들기」를 먼저 한다.
실행: $env:DB_PASSWORD = "비밀번호"; streamlit run app.py
"""
import streamlit as st

from utils.constants import DB_NAME
from views import codes, markets, parts, trend, volume

st.set_page_config(page_title="자동차부품 무역 대시보드 (MySQL)", page_icon="🚗", layout="wide")
# wide 는 화면 끝까지 퍼져서 읽기 힘들고, centered 는 지표 이름이 잘린다. 본문 폭을 1060px 로 묶는다.
st.markdown('<style>[data-testid="stMainBlockContainer"]{max-width:1060px}</style>', unsafe_allow_html=True)

# 메뉴에 보이는 이름 → 그 페이지를 그리는 함수
PAGES = {
    "전체 흐름": trend.show_trend,
    "부품별 무역수지": parts.show_parts,
    "나라별 비중": markets.show_markets,
    "금액과 중량": volume.show_volume,
    "부품 코드 안내": codes.show_codes,
}

page = st.sidebar.selectbox("페이지 선택", list(PAGES), key="page")
st.sidebar.caption(f"데이터: MySQL {DB_NAME}")
PAGES[page]()
