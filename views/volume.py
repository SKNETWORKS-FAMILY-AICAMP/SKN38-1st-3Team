import altair as alt
import pandas as pd
import streamlit as st

from utils.common import (
    aggregate,
    format_country,
    period_filter_controls,
    format_number,
    format_percent_value,
    growth,
    header,
    format_metric_value,
)
from utils.constants import COUNTRIES, MONTHS
from utils.parts_catalog import ITEMS


def calculate_export_metrics(current, previous):
    export_total = current["수출액"].sum()
    previous_export_total = previous["수출액"].sum()
    weight_total = current["수출중량"].sum()
    previous_weight_total = previous["수출중량"].sum()
    unit_value = export_total * 1000 / weight_total if weight_total else 0
    previous_unit_value = None
    if previous_weight_total:
        previous_unit_value = previous_export_total * 1000 / previous_weight_total

    return {
        "export_total": export_total,
        "weight_total": weight_total,
        "unit_value": unit_value,
        "export_growth": growth(export_total, previous_export_total),
        "weight_growth": growth(weight_total, previous_weight_total),
        "unit_growth": growth(unit_value, previous_unit_value),
    }


def volume_page():
    # 1. 필터
    filters = period_filter_controls()
    start = filters["start"]
    end = filters["end"]
    header(
        "03 금액과 중량",
        "수출액이 늘어난 만큼 수출 물량(중량)도 늘었나?",
    )
    item_labels = {"자동차부품 전체": "all"}
    item_labels.update({f"{name} ({code})": code for code, name in ITEMS})
    item_col, country_col = st.columns(2)
    with item_col:
        selected_item = st.selectbox("부품", list(item_labels), key="item")
    with country_col:
        selected_country = st.selectbox(
            "상대국",
            ["10개국 전체"] + COUNTRIES,
            format_func=format_country,
            key="country",
        )
    item_code = item_labels[selected_item]
    country = "all" if selected_country == "10개국 전체" else selected_country
    selected_item_name = (
        "자동차부품 전체"
        if item_code == "all"
        else next(name for code, name in ITEMS if code == item_code)
    )

    # 2. 계산
    current, previous = aggregate(start, end, item_code, country)
    metrics = calculate_export_metrics(current, previous)
    export_sum = metrics["export_total"]
    weight_sum = metrics["weight_total"]
    unit_value = metrics["unit_value"]
    export_growth = metrics["export_growth"]
    weight_growth = metrics["weight_growth"]
    unit_growth = metrics["unit_growth"]
    export_delta = f"{format_metric_value(export_growth)}% (작년 같은 기간 대비)"
    weight_delta = f"{format_metric_value(weight_growth)}% (작년 같은 기간 대비)"
    unit_delta = f"{format_metric_value(unit_growth)}% (작년 같은 기간 대비)"

    # 3. 지표 카드
    first, second, third = st.columns(3)
    first.metric(
        f"{MONTHS[start]}–{MONTHS[end]} 수출액 증감률",
        f"{format_metric_value(export_growth)}%",
        export_delta,
        delta_color="normal",
        border=True,
    )
    second.metric(
        f"{MONTHS[start]}–{MONTHS[end]} 수출중량 증감률",
        f"{format_metric_value(weight_growth)}%",
        weight_delta,
        delta_color="normal",
        border=True,
    )
    third.metric(
        "kg당 수출액",
        f"{unit_value:.2f} 달러/kg",
        unit_delta,
        delta_color="normal",
        border=True,
    )
    # 4. 계산과 차트
    st.subheader("수출액과 수출중량 증감률")
    place = "10개국 전체" if country == "all" else country
    st.caption(f"{MONTHS[start]}–{MONTHS[end]} · {place} · {selected_item_name}")
    display_frame = pd.DataFrame(
        [
            {
                "부품": selected_item_name,
                "코드": "전체" if item_code == "all" else item_code,
                "수출액 (백만 달러)": export_sum,
                "수출액 증감률 (%)": export_growth,
                "수출중량 (톤)": weight_sum,
                "수출중량 증감률 (%)": weight_growth,
                "킬로당 금액 증감률 (%)": unit_growth,
            }
        ]
    )
    melted = pd.melt(
        display_frame,
        id_vars=["부품", "코드"],
        value_vars=["수출액 증감률 (%)", "수출중량 증감률 (%)"],
        var_name="항목",
        value_name="증감률",
    )
    melted["항목"] = melted["항목"].replace(
        {
            "수출액 증감률 (%)": "수출액",
            "수출중량 증감률 (%)": "수출중량",
        }
    )
    melted["대상 국가"] = place
    melted["기간"] = f"{MONTHS[start]}–{MONTHS[end]}"
    zero_line = (
        alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#687583").encode(x="x:Q")
    )
    growth_chart = (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            y=alt.Y(
                "부품:N",
                sort=display_frame["부품"].tolist(),
                title=None,
            ),
            x=alt.X("증감률:Q", title="증감률 (%)"),
            yOffset="항목:N",
            color=alt.Color(
                "항목:N",
                scale=alt.Scale(
                    domain=["수출액", "수출중량"],
                    range=["#1d58b0", "#7a55c7"],
                ),
            ),
            tooltip=[
                "부품:N",
                alt.Tooltip("대상 국가:N", title="대상 국가"),
                alt.Tooltip("기간:N", title="기간"),
                "항목:N",
                alt.Tooltip("증감률:Q", format="+.1f", title="증감률 (%)"),
            ],
        )
    )
    st.altair_chart(zero_line + growth_chart, width="stretch")

    # 5. 표
    st.dataframe(
        display_frame.style.format(
            {
                "수출액 (백만 달러)": lambda value: format_number(value, 1),
                "수출중량 (톤)": lambda value: format_number(value, 1),
                "수출액 증감률 (%)": format_percent_value,
                "수출중량 증감률 (%)": format_percent_value,
                "킬로당 금액 증감률 (%)": format_percent_value,
            },
            na_rep="—",
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption("kg당 금액 = 수출액 ÷ 수출중량. 판매 가격이 아닌 대용치")
