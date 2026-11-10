import streamlit as st

from utils.common import header
from utils.constants import TERMS


def faq_page():
    header("FAQ", "용어와 화면 이용 방법")

    st.subheader("수치와 무역 용어")
    for term, explanation in TERMS:
        with st.expander(term):
            st.write(explanation)

    st.subheader("HS 코드 관련 문의")
    questions_hs = [
        ("8708.30-1000은 어떻게 읽나요?", "HS 코드는 상품을 분류하는 번호로, 앞자리부터 큰 분류에서 작은 분류로 좁혀집니다.\n\n"
            "예를 들어 **87**은 차량이 속한 분류, **8708**은 자동차 부분품, "
            "**8708.30**은 제동장치, **8708.30-1000**은 국내 세분까지 나타냅니다."),
        ("8708번 코드가 무엇인가요?", "- 8708은 제8701호부터 제8705호까지 차량용 부분품·부속품을 다룹니다.\n"
            "- 제17부 주 2: 조인트·와셔 등 유사품, 제15부 주 2의 범용성 부분품, "
            "제82류 공구, 제8311호 물품을 제외합니다.\n"
            "- 제8401~8459호·제8461호·제8462호 기계류와 제8463호 원동기 부분품, "
            "제85류 전기기기도 제외합니다.\n"
            "- 제90류 물품, 제91류 시계, 제93류 무기, 차량 부분품용 브러시(제9601호)도 제외합니다."),
        ("출처가 어떻게 되나요?", 
        "아래와 같은 출처에서 데이터를 참고합니다." 
        "- [관세법령정보포털 CLIP 관세율표 세번 조회]"
        "(https://unipass.customs.go.kr/clip/hsinfosrch/openULS0201008Q.do)\n"
        "- [WCO HS 2022, Section XVII / Chapter 87]"
        "(https://www.wcoomd.org/-/media/wco/public/global/pdf/topics/nomenclature/"
        "instruments-and-tools/hs-nomenclature-2022/2022/1787_2022e.pdf?la=en)\n"
        "- [국가법령정보센터 관세율표 제17부]"
        "(https://www.law.go.kr/LSW/flDownload.do?flNm=%5B별표+%5D+"
        "%EC%84%B8%EC%9C%A8%ED%91%9C%0A&flSeq=88844851)" )
    ]

    for question, answer in questions_hs:
        with st.expander(question):
            st.write(answer)

    st.subheader("화면과 데이터")
    questions_screen = [
        (
            "기간을 선택하면 어떤 값이 나오나요?",
            "시작 월부터 끝 월까지의 합계와 비중을 보여줍니다. "
            "변화 그래프는 선택한 기간의 첫 달과 마지막 달을 비교합니다.",
        ),
        (
            "나라별 비중은 한국 전체 기준인가요?",
            "아니요. 이 화면에 포함된 상대국 10개국 합계 안에서의 비중입니다. "
            "한국 전체 수출입에서 차지하는 비율은 아닙니다.",
        ),
        (
            "수출액이 늘면 수출 물량도 늘어난 건가요?",
            "꼭 그렇지는 않습니다. 금액과 중량을 따로 비교하세요. "
            "kg당 금액은 판매 가격이 아니라 가격을 짐작하기 위한 대용치입니다.",
        ),
        (
            "표는 어떻게 정렬하나요?",
            "표의 열 제목 메뉴에서 오름차순 또는 내림차순을 선택할 수 있습니다.",
        ),
    ]
    for question, answer in questions_screen:
        with st.expander(question):
            st.write(answer)
