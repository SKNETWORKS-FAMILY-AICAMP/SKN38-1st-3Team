"""02 나라별 비중: 수출·수입 상대국 비중 막대와 표.

데이터 함수: get_country_share
그리는 함수: show_markets — app.py 가 부른다.
샘플 markets.py 에서 고친 곳:
- ×200(markets.py:51): 분모에 전세계 합계 줄("-")이 같이 더해져 두 배가 된 것을 맞춘 값이다. 합계 줄을 빼고 ×100 으로 낸다.
- 작년 대비(markets.py:106): 이번·작년 표를 줄 순서로 뺐다. 한쪽에만 있는 나라가 있으면 다른 나라끼리 빠진다.
  여기서는 한 쿼리에서 나라마다 이번·작년 비중을 같이 낸다.
- 기타 묶음(markets.py:94)은 utils/common.part_where 참고.
"""
import altair as alt
import pandas as pd
import streamlit as st

from utils import common as c
from utils.constants import EXPORT_COLOR, IMPORT_COLOR, WORLD
from utils.db import query


# ---------- 데이터 함수 ----------

def get_country_share(f: dict) -> pd.DataFrame:
    """10개국 합계 = 100% 로 본 나라별 수출·수입 비중(%), 이번 기간과 작년 같은 기간.

    실적이 없는 나라도 0으로 나오게 나라 목록에 붙인다. 합계가 0이면 비중은 NULL(화면에서 「실적 없음」).
    """
    where, wparams = c.part_where(f["part"])
    s, e, ps, pe = f["start"], f["end"], f["pstart"], f["pend"]
    return query(f"""
        WITH countries AS (
            SELECT DISTINCT statCd FROM trades WHERE statCd <> '{WORLD}'
        ),
        sums AS (
            SELECT
                t.statCd,
                SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.expDlr ELSE 0 END) AS cur_exp,
                SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.impDlr ELSE 0 END) AS cur_imp,
                SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.expDlr ELSE 0 END) AS prev_exp,
                SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.impDlr ELSE 0 END) AS prev_imp
            FROM trades t
            WHERE t.statCd <> '{WORLD}' AND {where}
            GROUP BY t.statCd
        ),
        filled AS (
            SELECT
                st.statKor AS country,
                COALESCE(s.cur_exp, 0)  AS cur_exp,
                COALESCE(s.cur_imp, 0)  AS cur_imp,
                COALESCE(s.prev_exp, 0) AS prev_exp,
                COALESCE(s.prev_imp, 0) AS prev_imp
            FROM countries co
            JOIN stats st ON st.statCd = co.statCd
            LEFT JOIN sums s ON s.statCd = co.statCd
        )
        SELECT
            country,
            100 * cur_exp  / NULLIF(SUM(cur_exp)  OVER (), 0) AS exp_share,
            100 * cur_imp  / NULLIF(SUM(cur_imp)  OVER (), 0) AS imp_share,
            100 * prev_exp / NULLIF(SUM(prev_exp) OVER (), 0) AS prev_exp_share,
            100 * prev_imp / NULLIF(SUM(prev_imp) OVER (), 0) AS prev_imp_share
        FROM filled
        ORDER BY country
    """, (s, e, s, e, ps, pe, ps, pe) + wparams)


# ---------- 그리는 함수 ----------

def show_markets() -> None:
    c.header("02 부품·시장", "어느 나라로 수출하고, 어느 나라에서 수입하나?")
    f = c.filters(part=True, country=False)
    c.prev_note(f)

    s = get_country_share(f)
    part_label = c.get_part_names().get(f["part"], f["part"])
    columns = st.columns(2)
    specs = [("exp", "수출: 어느 나라로 가나", "수출", EXPORT_COLOR),
             ("imp", "수입: 어느 나라에서 오나", "수입", IMPORT_COLOR)]

    for col, (key, title, word, color) in zip(columns, specs):
        with col:
            st.subheader(title)
            st.caption(f"{part_label} · {c.period_text(f)} · 10개국 합계 = 100%")
            share = s[f"{key}_share"]
            if share.isna().all():
                st.info(f"이 기간에 {word} 실적이 없습니다.")
                continue
            prev = s[f"prev_{key}_share"].fillna(0)  # 작년 실적이 없으면 작년 비중을 모두 0으로 본다
            t = pd.DataFrame({
                "나라": s["country"],
                "비중 (%)": share,
                "작년 대비 비중 변화(%p)": share - prev,
            }).sort_values("비중 (%)", ascending=False, kind="stable")  # 비중이 같으면 나라 이름순(SQL ORDER BY)

            bar = alt.Chart(t).mark_bar(color=color).encode(
                y=alt.Y("나라:N", sort=None, title=None),
                x=alt.X("비중 (%):Q", title="비중 (%)"),
                tooltip=["나라", alt.Tooltip("비중 (%):Q", format=".1f")],
            )
            st.altair_chart(bar.properties(height=280))
            st.dataframe(
                t.style.format({"비중 (%)": "{:.1f}%", "작년 대비 비중 변화(%p)": "{:+.1f}%p"}),
                hide_index=True,
            )
