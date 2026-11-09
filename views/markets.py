import altair as alt
import pandas as pd
import streamlit as st

from utils.common import (
    aggregate,
    filter_controls,
    format_number,
    format_signed_value,
    header,
)
from utils.constants import COUNTRIES, ITEMS, MONTHS

def format_share(value):
    return f"{format_number(value, 1)}%"


def format_share_change(value):
    return f"{format_signed_value(value)}%p"


def markets_page():
    # 1. 필터
    filters = filter_controls(use_item=True)
    start = filters["start"]
    end = filters["end"]
    item_code = filters["item_code"]
    header("02 부품·시장", "어느 나라로 수출하고, 어느 나라에서 수입하나?")

    # 2. 계산
    current, previous = aggregate(start, end, item_code=item_code)
    columns = st.columns(2)
    measures = ["수출액", "수입액"]
    titles = ["수출: 어느 나라로 가나", "수입: 어느 나라에서 오나"]
    for column, measure, title in zip(columns, measures, titles):
        measure_total = current[measure].sum()
        previous_sum = previous[measure].sum()
        rows = []
        for country in COUNTRIES:
            current_share = 0
            previous_share = 0
            if measure_total:
                current_share = (
                    current[current["나라"] == country][measure].sum()
                    / measure_total
                    * 100
                )
            if previous_sum:
                previous_share = (
                    previous[previous["나라"] == country][measure].sum()
                    / previous_sum
                    * 100
                )
            rows.append(
                {
                    "나라": country,
                    "비중 (%)": current_share,
                    "작년 대비 비중 변화(%p)": current_share - previous_share,
                }
            )
        frame = pd.DataFrame(rows)
        country_order = frame.sort_values("비중 (%)", ascending=False)
        country_order = country_order["나라"].tolist()
        frame = frame.set_index("나라").loc[country_order].reset_index()

        item_name = "자동차부품 전체"
        if item_code != "all":
            item_name = next(item[1] for item in ITEMS if item[0] == item_code)
        with column:
            st.subheader(title)
            st.caption(
                f"{item_name} · {MONTHS[start]}–{MONTHS[end]} · "
                "10개국 합계 = 100%"
            )
            # 3. 차트
            share_chart = (
                alt.Chart(frame)
                .mark_bar()
                .encode(
                    y=alt.Y("나라:N", sort=country_order, title=None),
                    x=alt.X("비중 (%):Q", title="비중 (%)"),
                    tooltip=[
                        "나라:N",
                        alt.Tooltip("비중 (%):Q", format=".1f"),
                        alt.Tooltip(
                            "작년 대비 비중 변화(%p):Q",
                            format="+.1f",
                        ),
                    ],
                )
            )
            st.altair_chart(share_chart, width="stretch")
            # 4. 표
            styled_frame = frame.style.format(
                {
                    "비중 (%)": format_share,
                    "작년 대비 비중 변화(%p)": format_share_change,
                }
            )
            st.dataframe(styled_frame, hide_index=True, width="stretch")
