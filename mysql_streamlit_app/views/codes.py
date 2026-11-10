"""04 부품 코드 안내: 코드 읽는 법, 데이터에 있는 코드 설명, 용어와 계산 방법.

데이터 함수: get_codes
그리는 함수: show_codes — app.py 가 부른다.
"""
import pandas as pd
import streamlit as st

from utils import common as c
from utils.constants import ALL_PARTS_CODE, NOTE, TERMS, WORLD
from utils.db import query


# ---------- 데이터 함수 ----------

def get_codes() -> pd.DataFrame:
    """데이터에 있는 10자리 코드 25개와 6자리 소호, 기타 묶음 여부, 데이터가 있는 기간."""
    return query(f"""
        SELECT
            t.hsCd                                              AS `코드`,
            CONCAT(LEFT(t.hsCd, 4), '.', SUBSTRING(t.hsCd, 5, 2)) AS `소호(6자리)`,
            MAX(p.hsKor)                                        AS `부품 이름`,
            MAX(p.hsExp)                                        AS `원문 이름`,
            CASE WHEN MAX({c.PART_KEY}) = '기타' THEN '기타' ELSE '' END AS `화면 묶음`,
            MIN(t.year)                                         AS `데이터 시작`,
            MAX(t.year)                                         AS `데이터 끝`
        FROM trades t
        JOIN parts p ON p.hsCd = t.hsCd
        WHERE t.hsCd <> '{ALL_PARTS_CODE}' AND t.statCd <> '{WORLD}'
        GROUP BY t.hsCd
        ORDER BY t.hsCd
    """)


# ---------- 그리는 함수 ----------

def show_codes() -> None:
    st.caption("04 부품 코드 안내")
    st.title("부품 코드는 어떻게 읽나?")
    st.info(NOTE)

    st.subheader("코드 읽는 법")
    st.markdown(
        """
예: **8708 40 0000** (기어박스와 그 부분품)

| 자리 | 예 | 뜻 |
|---|---|---|
| 앞 2자리 | 87 | 류: 철도 외의 차량과 그 부분품 |
| 앞 4자리 | 8708 | 호: 자동차(8701~8705호 차량)의 부분품과 부속품. 이 앱의 모든 코드는 8708로 시작한다 |
| 앞 6자리 | 8708.40 | 소호: 세계 공통으로 쓰는 6자리 분류 |
| 10자리 | 8708400000 | 한국에서 더 잘게 나눈 분류(HSK) |
"""
    )

    t = get_codes()
    st.subheader(f"데이터에 있는 부품 코드 {len(t)}개")
    st.caption("「화면 묶음」이 기타인 6개 코드는 다른 페이지에서 「기타」 한 줄로 합쳐 보여 준다.")
    st.dataframe(t, hide_index=True, height=420, column_config={
        "부품 이름": st.column_config.TextColumn(width=260),
        "원문 이름": st.column_config.TextColumn(width=420),
    })

    st.subheader("용어와 계산 방법")
    st.dataframe(pd.DataFrame(TERMS, columns=["용어", "뜻과 계산"]), hide_index=True)
