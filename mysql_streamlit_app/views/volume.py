"""03 금액과 중량: 수출액·수출중량 증감률과 kg당 수출액, 부품별 증감률 비교.

데이터 함수: get_part_growth (지표 합계는 utils/common.get_period_totals)
그리는 함수: show_volume — app.py 가 부른다.
"""
import altair as alt
import pandas as pd
import streamlit as st

from utils import common as c
from utils.constants import ALL_PARTS_CODE, EXPORT_COLOR, WEIGHT_COLOR
from utils.db import query


# ---------- 데이터 함수 ----------

def get_part_growth(f: dict) -> pd.DataFrame:
    """부품별 수출액·수출중량 증감률(%). 맨 위에 「자동차부품 전체」(합계 줄 8708000000) 한 줄.

    작년 같은 기간 값이 0이면 0으로 나눌 수 없어 증감률은 NULL(화면에서 「작년 없음」으로 막대에서 뺀다).
    """
    s, e, ps, pe = f["start"], f["end"], f["pstart"], f["pend"]
    sums = """
        SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.expDlr ELSE 0 END) AS cur_exp_usd,
        SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.expwgt ELSE 0 END) AS cur_exp_kg,
        SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.expDlr ELSE 0 END) AS prev_exp_usd,
        SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.expwgt ELSE 0 END) AS prev_exp_kg"""
    period = "(t.year BETWEEN %s AND %s OR t.year BETWEEN %s AND %s)"
    p_sums = (s, e, s, e, ps, pe, ps, pe)
    p_where = (f["cc"], s, e, ps, pe)
    return query(f"""
        WITH per_part AS (
            SELECT '자동차부품 전체' AS part_name, 1 AS is_total, {sums}
            FROM trades t
            WHERE t.statCd = %s AND t.hsCd = '{ALL_PARTS_CODE}' AND {period}
            UNION ALL
            SELECT MAX({c.PART_NAME}) AS part_name, 0 AS is_total, {sums}
            FROM trades t
            JOIN parts p ON p.hsCd = t.hsCd
            WHERE t.statCd = %s AND t.hsCd <> '{ALL_PARTS_CODE}' AND {period}
            GROUP BY {c.PART_KEY}
        )
        SELECT
            part_name,
            is_total,
            (cur_exp_usd / NULLIF(prev_exp_usd, 0) - 1) * 100 AS usd_growth,
            (cur_exp_kg  / NULLIF(prev_exp_kg, 0) - 1) * 100  AS kg_growth
        FROM per_part
        ORDER BY is_total DESC, usd_growth IS NULL, usd_growth DESC
    """, p_sums + p_where + p_sums + p_where)


# ---------- 그리는 함수 ----------

def _unit_price(s: pd.Series) -> float | None:
    if s.exp_kg == 0:
        return None
    return s.exp_usd / s.exp_kg


def show_volume() -> None:
    c.header("03 금액과 중량", "수출액이 늘어난 만큼 수출 물량(중량)도 늘었나?")
    f = c.filters(part=True, country=True)
    c.prev_note(f)

    cur, prev = c.get_period_totals(f)
    g_usd = c.pct(cur.exp_usd, prev.exp_usd)
    g_kg = c.pct(cur.exp_kg, prev.exp_kg)
    up_cur, up_prev = _unit_price(cur), _unit_price(prev)
    g_up = None if up_cur is None else c.pct(up_cur, up_prev)

    label = c.period_text(f)
    k1, k2, k3 = st.columns(3)
    k1.metric(f"{label} 수출액 증감률", c.pct_text(g_usd), c.yoy_text(g_usd), delta_color="off", border=True)
    k2.metric(f"{label} 수출중량 증감률", c.pct_text(g_kg), c.yoy_text(g_kg), delta_color="off", border=True)
    k3.metric("kg당 수출액", "수출 없음" if up_cur is None else f"{up_cur:,.2f} 달러/kg", c.yoy_text(g_up),
              delta_color="off", border=True)
    st.caption(f"달러 기준 · 수출액 {c.musd(cur.exp_usd)} 백만 달러 · 수출중량 {cur.exp_kg / 1000:,.0f} 톤")

    st.subheader("부품별 수출액과 수출중량 증감률")

    # 부품 선택과 상관없이 모든 부품을 견준다(상대국 선택만 따른다).
    g = get_part_growth(f)
    ok = g["usd_growth"].notna() & g["kg_growth"].notna()
    skipped = g.loc[~ok, "part_name"].tolist()
    t = g[ok].rename(columns={"part_name": "부품", "usd_growth": "수출액", "kg_growth": "수출중량"})[["부품", "수출액", "수출중량"]]
    if t.empty:
        st.info("모든 부품이 작년 같은 기간 수출 0이라 증감률을 그릴 수 없습니다(작년 없음).")
        return

    st.caption(f"{label} · {f['country']} · 수출액 증감률이 큰 부품부터 · 위 지표와 달리 부품 선택은 적용하지 않음")
    long = t.melt("부품", var_name="항목", value_name="증감률")
    # 수출이 적은 부품은 수백 %가 나와서 나머지 막대가 안 보인다. 축을 CAP 에서 자르고 실제 값은 툴팁으로 보인다.
    # 되돌리려면 scale 을 지운다.
    CAP = 200
    clipped = long["증감률"].gt(CAP).any()  # 감소는 −100%가 끝이라 위쪽만 자른다
    lo = min(0.0, float(long["증감률"].min()))
    st.caption("가운데 선 오른쪽 = 증가, 왼쪽 = 감소"
               + (f" · +{CAP}%를 넘는 막대는 끝을 잘랐다(마우스를 올리면 실제 값)" if clipped else ""))
    bars = alt.Chart(long).mark_bar().encode(
        y=alt.Y("부품:N", sort=list(t["부품"]), title=None, axis=alt.Axis(labelLimit=260)),
        yOffset=alt.YOffset("항목:N", sort=["수출액", "수출중량"]),
        x=alt.X("증감률:Q", title="작년 같은 기간 대비 증감률 (%)",
                scale=alt.Scale(domain=[lo, CAP], clamp=True) if clipped else alt.Undefined),
        color=alt.Color("항목:N", scale=alt.Scale(domain=["수출액", "수출중량"], range=[EXPORT_COLOR, WEIGHT_COLOR])),
        tooltip=["부품", "항목", alt.Tooltip("증감률:Q", format="+.1f")],
    )
    rule = alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#555").encode(x="x:Q")
    st.altair_chart((bars + rule).properties(height=len(t) * 36 + 40))
    if skipped:
        st.caption("작년 없음(작년 같은 기간 수출액이나 중량 0)이라 막대에서 뺀 부품: " + ", ".join(skipped))
