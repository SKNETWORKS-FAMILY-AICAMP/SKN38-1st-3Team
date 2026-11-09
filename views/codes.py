import pandas as pd
import streamlit as st

from utils.common import header
from utils.constants import CODE_GUIDE_GROUPS, TERMS


def display_code(code):
    if code == "기타":
        return code
    return f"{code[:4]}.{code[4:6]}-{code[6:]}"


def render_item(item):
    with st.container(border=True):
        left, right = st.columns([1, 3])
        with left:
            with st.container(border=True, height=120):
                st.caption("이미지 준비 중")
        with right:
            st.subheader(f"{item['display_name']} · {display_code(item['hsCd'])}")
            st.write(item["plain_description"])
            st.caption(f"공식 품명: {item['official_name']}")
            st.markdown("**포함 예시**: " + "、".join(item["includes"]))
            if item["caution"]:
                st.caption("주의: " + item["caution"])


def codes_page():
    # 1. 코드 읽는 법
    header("부품 코드 안내", "HS 8708 부품 코드는 각각 무엇인가?")
    st.subheader("코드 읽는 법")
    st.caption(
        "무역 통계는 상품을 HS 코드로 나눕니다. 이 대시보드는 "
        "자동차부품(8708)을 10자리 코드 20개로 나눠 봅니다."
    )
    st.markdown(
        "**87** 차량 → **8708** 자동차 부분품·부속품 → "
        "**8708.30** 제동장치 → **8708.30-1000**"
    )

    # 2. 그룹별 코드 목록
    tabs = st.tabs([group_name for group_name, _ in CODE_GUIDE_GROUPS])
    for tab, (group_name, items) in zip(tabs, CODE_GUIDE_GROUPS):
        with tab:
            for item in items:
                render_item(item)

    # 3. 제외 대상
    st.subheader("8708에 들어가지 않는 것")
    st.markdown(
        "- 8708은 제8701호부터 제8705호까지 차량용 부분품·부속품을 다룹니다.\n"
        "- 제17부 주 2: 조인트·와셔 등 유사품, 제15부 주 2의 범용성 부분품, "
        "제82류 공구, 제8311호 물품을 제외합니다.\n"
        "- 제8401~8459호·제8461호·제8462호 기계류와 제8463호 원동기 부분품, "
        "제85류 전기기기도 제외합니다.\n"
        "- 제90류 물품, 제91류 시계, 제93류 무기, 차량 부분품용 브러시(제9601호)도 제외합니다."
    )

    # 4. 출처와 용어
    with st.expander("출처"):
        st.markdown(
            "- [관세법령정보포털 CLIP 관세율표 세번 조회]"
            "(https://unipass.customs.go.kr/clip/hsinfosrch/openULS0201008Q.do)\n"
            "- [WCO HS 2022, Section XVII / Chapter 87]"
            "(https://www.wcoomd.org/-/media/wco/public/global/pdf/topics/nomenclature/"
            "instruments-and-tools/hs-nomenclature-2022/2022/1787_2022e.pdf?la=en)\n"
            "- [국가법령정보센터 관세율표 제17부]"
            "(https://www.law.go.kr/LSW/flDownload.do?flNm=%5B%EB%B3%84%ED%91%9C+%5D+"
            "%EC%84%B8%EC%9C%A8%ED%91%9C%0A&flSeq=88844851)\n"
            "- 자동차 부품 HS 표준해석 지침 사례: `scratchpad/codex/hs8708_codes.md`"
        )

    st.subheader("용어와 계산 방법")
    terms_frame = pd.DataFrame(TERMS, columns=["용어", "설명"])
    st.dataframe(terms_frame, hide_index=True, width="stretch")
    st.caption(
        "화면 설계 검토용 프로토타입 · 모든 수치는 가상 데이터이며 "
        "관세청·한국은행 통계와 연결되어 있지 않습니다."
    )
