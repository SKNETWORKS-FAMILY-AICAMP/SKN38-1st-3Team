import streamlit as st

from views.codes import codes_page
from views.faq import faq_page
from views.markets import markets_page
from views.parts import parts_page
from views.trend import trend_page
from views.volume import volume_page

st.set_page_config(
    page_title="자동차부품 무역 대시보드",
    page_icon="🚗",
    layout="wide",
)

page_names_to_funcs = {
    "전체 흐름": trend_page,
    "부품별 무역수지": parts_page,
    "나라별 비중": markets_page,
    "금액과 중량": volume_page,
    "부품 코드 안내": codes_page,
    "FAQ · 용어 안내": faq_page,
}
st.sidebar.title("자동차부품 무역 대시보드")
st.sidebar.divider()

selected_page = st.sidebar.selectbox(
    "메뉴",
    page_names_to_funcs.keys(),
    key="selected_page",
)
page_names_to_funcs[selected_page]()
