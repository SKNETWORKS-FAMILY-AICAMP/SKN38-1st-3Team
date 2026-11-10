"""01 전체 흐름: 지표 3개, 월별 수출입 선 그래프, 연도별 무역수지 막대.

데이터 함수: get_monthly, get_yearly_balance (지표 합계는 utils/common.get_period_totals)
그리는 함수: show_trend — app.py 가 부른다.
샘플 trend.py 와 다른 점: host 줄의 문법 오류(trend.py:21 `"localhost",1`)가 없고, 비교 기간은 고정 묶음이 아니라 고른 달이다.
"""
import altair as alt
import pandas as pd
import streamlit as st

from utils import common as c
from utils.constants import ALL_PARTS_CODE, BAD_COLOR, EXPORT_COLOR, GOOD_COLOR, IMPORT_COLOR
from utils.db import query


# ---------- 데이터 함수 ----------

def get_monthly(cc: str) -> pd.DataFrame:
    """월별 수출액·수입액 (전체 기간). 부품 전체 합계 줄을 읽는다."""
    df = query(f"""
        SELECT t.year, SUM(t.expDlr) AS exp_usd, SUM(t.impDlr) AS imp_usd
        FROM trades t
        WHERE t.statCd = %s AND t.hsCd = '{ALL_PARTS_CODE}'
        GROUP BY t.year
        ORDER BY t.year
    """, (cc,))
    df.insert(0, "month", pd.to_datetime(df.pop("year"), format="%Y.%m"))
    return df


def get_yearly_balance(cc: str) -> pd.DataFrame:
    """연도별 무역수지. 1년이 다 차지 않은 해를 알 수 있게 달 수와 첫·끝 달을 같이 낸다."""
    return query(f"""
        SELECT LEFT(t.year, 4) AS year, SUM(t.balPayments) AS balance,
               COUNT(DISTINCT t.year) AS n_months, MIN(t.year) AS first_month, MAX(t.year) AS last_month
        FROM trades t
        WHERE t.statCd = %s AND t.hsCd = '{ALL_PARTS_CODE}'
        GROUP BY LEFT(t.year, 4)
        ORDER BY 1
    """, (cc,))


# ---------- 그리는 함수 ----------

def show_trend() -> None:
    c.header("01 전체 흐름", "자동차부품 무역수지는 어떻게 변하고 있나?")
    f = c.filters()
    c.prev_note(f)

    cur, prev = c.get_period_totals(f)

    label = f"{c.period_text(f)}"
    k1, k2, k3 = st.columns(3)
    k1.metric(f"{label} 수출액 (백만 달러)", c.musd(cur.exp_usd), c.yoy_text(c.pct(cur.exp_usd, prev.exp_usd)),
              delta_color="off", border=True)
    k2.metric(f"{label} 수입액 (백만 달러)", c.musd(cur.imp_usd), c.yoy_text(c.pct(cur.imp_usd, prev.imp_usd)),
              delta_color="off", border=True)
    bal_delta = f"{c.musd(cur.balance - prev.balance, 1, sign=True)} · {c.balance_status(cur.balance, prev.balance)}"
    k3.metric(f"{label} 무역수지 (백만 달러)", c.musd(cur.balance, sign=True), bal_delta, delta_color="off", border=True)

    # 월별 수출액과 수입액
    st.subheader("월별 수출액과 수입액")
    st.caption(f"{f['country']} · 백만 달러 · 음영 = 선택한 기간")
    monthly = get_monthly(f["cc"])
    monthly[["exp_usd", "imp_usd"]] /= 1e6
    long = monthly.melt("month", var_name="kind", value_name="value")
    long["kind"] = long["kind"].map({"exp_usd": "수출액", "imp_usd": "수입액"})

    band_df = pd.DataFrame({
        "s": [pd.Timestamp(f["start"].replace(".", "-"))],
        "e": [pd.Timestamp(f["end"].replace(".", "-")) + pd.offsets.MonthEnd(0)],
    })
    band = alt.Chart(band_df).mark_rect(color="#dbe4f3", opacity=0.8).encode(x="s:T", x2="e:T")
    line = alt.Chart(long).mark_line(strokeWidth=2).encode(
        x=alt.X("month:T", title="연도", axis=alt.Axis(format="%Y", tickCount="year")),
        y=alt.Y("value:Q", title="백만 달러"),
        color=alt.Color("kind:N", title=None,
                        scale=alt.Scale(domain=["수출액", "수입액"], range=[EXPORT_COLOR, IMPORT_COLOR])),
        tooltip=[alt.Tooltip("month:T", title="월", format="%Y.%m"), alt.Tooltip("kind:N", title="항목"),
                 alt.Tooltip("value:Q", title="백만 달러", format=",.1f")],
    )
    st.altair_chart((band + line).properties(height=340))

    # 연도별 무역수지
    st.subheader("연도별 무역수지")
    yearly = get_yearly_balance(f["cc"])
    yearly["label"] = [
        f"{y}" if n == 12 else f"{y} ({fi[-2:]}–{la[-2:]}월)"
        for y, n, fi, la in zip(yearly["year"], yearly["n_months"], yearly["first_month"], yearly["last_month"])
    ]
    yearly["value"] = yearly["balance"] / 1e6
    st.caption(f"{f['country']} · 백만 달러 · 1년이 다 차지 않은 해는 괄호에 들어 있는 달을 적었다")
    bar = alt.Chart(yearly[["label", "value"]]).mark_bar().encode(
        x=alt.X("label:N", title=None, sort=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("value:Q", title="무역수지 (백만 달러)"),
        color=alt.condition(alt.datum.value >= 0, alt.value(GOOD_COLOR), alt.value(BAD_COLOR)),
        tooltip=[alt.Tooltip("label:N", title="연도"), alt.Tooltip("value:Q", title="무역수지", format="+,.1f")],
    )
    st.altair_chart(bar.properties(height=280))
