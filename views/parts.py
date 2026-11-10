import altair as alt
import pandas as pd
import streamlit as st

from utils.common import (
    aggregate,
    format_country,
    period_filter_controls,
    format_number,
    format_signed_value,
    header,
    state,
)
from utils.constants import COUNTRIES, MONTHS
from utils.parts_catalog import ITEMS

def format_amount(value):
    return format_number(value, 1)


def parts_page():
    # 1. 필터
    filters = period_filter_controls()
    start = filters["start"]
    end = filters["end"]
    header("02 부품·시장", "부품별 무역수지 변화")
    (country_col,) = st.columns(1)
    with country_col:
        selected_country = st.selectbox(
            "상대국",
            ["10개국 전체"] + COUNTRIES,
            format_func=format_country,
            key="country",
        )
    country = "all" if selected_country == "10개국 전체" else selected_country

    # 2. 계산
    unit = "$M"
    rows = []
    for item_data in ITEMS:
        code = item_data[0]
        name = item_data[1]
        current, previous = aggregate(
            start,
            end,
            item_code=code,
            country=country,
        )
        export_sum = current["수출액"].sum()
        import_sum = current["수입액"].sum()
        previous_balance = previous["무역수지"].sum()
        balance = current["무역수지"].sum()
        rows.append(
            {
                "부품": name,
                "코드": code,
                f"수출액 ({unit})": export_sum,
                f"수입액 ({unit})": import_sum,
                f"무역수지 ({unit})": balance,
                "작년 대비 변화": balance - previous_balance,
                "상태": state(previous_balance, balance),
            }
        )
    frame = pd.DataFrame(rows).sort_values("작년 대비 변화")

    # 3. 안내와 표
    st.subheader("부품별 무역수지")
    place = "10개국 전체" if country == "all" else country
    st.caption(
        f"{MONTHS[start]}–{MONTHS[end]} · {place} · {unit} · "
        "무역수지가 많이 나빠진 순"
    )
    export_column = f"수출액 ({unit})"
    import_column = f"수입액 ({unit})"
    balance_column = f"무역수지 ({unit})"
    styled_frame = frame.style.format(
        {
            export_column: format_amount,
            import_column: format_amount,
            balance_column: format_signed_value,
            "작년 대비 변화": format_signed_value,
        }
    )
    st.dataframe(styled_frame, hide_index=True, width="stretch")

    # 4. 차트
    st.subheader("작년 같은 기간보다 무역수지가 얼마나 변했나?")
    zero_line = (
        alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#687583").encode(x="x:Q")
    )
    change_chart = (
        alt.Chart(frame)
        .mark_bar()
        .encode(
            y=alt.Y("부품:N", sort=frame["부품"].tolist(), title=None),
            x=alt.X("작년 대비 변화:Q", title=unit),
            color=alt.condition(
                "datum['작년 대비 변화'] >= 0",
                alt.value("#1b7f52"),
                alt.value("#be3f33"),
            ),
            tooltip=[
                "부품:N",
                "코드:N",
                alt.Tooltip("작년 대비 변화:Q", format=",.1f"),
            ],
        )
    )
    st.altair_chart(change_chart + zero_line, width="stretch")
