"""02 부품별 무역수지: 부품 표(나빠진 순)와 작년 대비 변화 막대.

데이터 함수: get_parts_balance
그리는 함수: show_parts — app.py 가 부른다.
샘플 parts.py 는 부품 25개마다 쿼리 2번(50번)을 돌리고 기타 6개를 파이썬에서 더했다.
여기서는 같은 CASE WHEN 합계를 GROUP BY 한 번으로 낸다. 기타 6개는 「기타」 한 줄로 묶는다.
"""
import altair as alt
import pandas as pd
import streamlit as st

from utils import common as c
from utils.constants import ALL_PARTS_CODE, BAD_COLOR, GOOD_COLOR
from utils.db import query


# ---------- 데이터 함수 ----------

def get_parts_balance(f: dict) -> pd.DataFrame:
    """부품마다 선택한 기간의 수출액·수입액·무역수지와 작년 같은 기간 무역수지. 무역수지가 많이 나빠진 순.

    두 기간 중 한쪽에만 실적이 있으면 다른 쪽은 0이다. 부품 전체 합계 줄(8708000000)은 뺀다.
    """
    s, e, ps, pe = f["start"], f["end"], f["pstart"], f["pend"]
    return query(f"""
        SELECT part_key, part_name,
               CASE WHEN part_key = '기타' THEN '8708959000 외 5개' ELSE part_key END AS code_label,
               cur_exp_usd, cur_imp_usd, cur_balance, prev_balance
        FROM (
            SELECT
                {c.PART_KEY} AS part_key,
                MAX({c.PART_NAME}) AS part_name,
                SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.expDlr ELSE 0 END)      AS cur_exp_usd,
                SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.impDlr ELSE 0 END)      AS cur_imp_usd,
                SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.balPayments ELSE 0 END) AS cur_balance,
                SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.balPayments ELSE 0 END) AS prev_balance
            FROM trades t
            JOIN parts p ON p.hsCd = t.hsCd
            WHERE t.statCd = %s AND t.hsCd <> '{ALL_PARTS_CODE}'
              AND (t.year BETWEEN %s AND %s OR t.year BETWEEN %s AND %s)
            GROUP BY part_key
        ) x
        ORDER BY cur_balance - prev_balance, part_key
    """, (s, e, s, e, s, e, ps, pe, f["cc"], s, e, ps, pe))


# ---------- 그리는 함수 ----------

def show_parts() -> None:
    c.header("02 부품·시장", "어느 부품의 무역수지가 나빠지거나 좋아졌나?")
    f = c.filters()
    c.prev_note(f)

    s = get_parts_balance(f)
    t = pd.DataFrame({
        "부품": s["part_name"],
        "코드": s["code_label"],
        "수출액 (백만 달러)": s["cur_exp_usd"] / 1e6,
        "수입액 (백만 달러)": s["cur_imp_usd"] / 1e6,
        "무역수지 (백만 달러)": s["cur_balance"] / 1e6,
        "작년 대비 변화": (s["cur_balance"] - s["prev_balance"]) / 1e6,
        "상태": [c.balance_status(b, pb) for b, pb in zip(s["cur_balance"], s["prev_balance"])],
    })

    st.subheader("부품별 무역수지")
    st.caption(f"{c.period_text(f)} · {f['country']} · 백만 달러 · 무역수지가 많이 나빠진 순")
    if t.empty:
        st.info("이 기간과 작년 같은 기간 모두 거래 실적이 없습니다.")
        return
    st.dataframe(
        t.style.format({
            "수출액 (백만 달러)": "{:,.1f}", "수입액 (백만 달러)": "{:,.1f}",
            "무역수지 (백만 달러)": "{:+,.1f}", "작년 대비 변화": "{:+,.1f}",
        }),
        hide_index=True, height=420,
        column_config={"부품": st.column_config.TextColumn(width=280)},  # 긴 부품 이름이 잘리지 않게
    )

    st.subheader("작년 같은 기간보다 무역수지가 얼마나 변했나?")
    st.caption(f"{c.period_text(f)} · {f['country']} · 백만 달러 · 오른쪽 = 좋아짐, 왼쪽 = 나빠짐")
    bar = alt.Chart(t).mark_bar().encode(
        y=alt.Y("부품:N", sort=None, title=None, axis=alt.Axis(labelLimit=260)),
        x=alt.X("작년 대비 변화:Q", title="작년 대비 무역수지 변화 (백만 달러)"),
        color=alt.condition(alt.datum["작년 대비 변화"] >= 0, alt.value(GOOD_COLOR), alt.value(BAD_COLOR)),
        tooltip=["부품", "코드", alt.Tooltip("작년 대비 변화:Q", format="+,.1f"), "상태"],
    )
    rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#555").encode(x="x:Q")
    st.altair_chart((bar + rule).properties(height=len(t) * 24 + 40))
