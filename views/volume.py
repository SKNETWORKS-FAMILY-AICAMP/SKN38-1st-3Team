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
    st.caption(
        f"달러 기준 · 수출액 {format_number(export_sum)} 백만 달러 · "
        f"수출중량 {format_number(weight_sum)} 톤"
    )

    # 4. 계산과 차트
    st.subheader("부품별 수출액과 수출중량 증감률")
    place = "10개국 전체" if country == "all" else country
    st.caption(
        f"{MONTHS[start]}–{MONTHS[end]} · {place} · " "수출액 증감률이 큰 부품부터"
    )
    rows = []
    for item_data in ITEMS:
        code = item_data[0]
        name = item_data[1]
        item_current, item_previous = aggregate(start, end, code, country)
        item_metrics = calculate_export_metrics(item_current, item_previous)
        rows.append(
            {
                "부품": name,
                "코드": code,
                "수출액 증감률 (%)": item_metrics["export_growth"],
                "수출중량 증감률 (%)": item_metrics["weight_growth"],
                "kg당 금액 증감률 (%)": item_metrics["unit_growth"],
            }
        )

    whole_current, whole_previous = aggregate(start, end, "all", country)
    whole_metrics = calculate_export_metrics(whole_current, whole_previous)
    total_row = {
        "부품": "자동차부품 전체",
        "코드": "전체",
        "수출액 증감률 (%)": whole_metrics["export_growth"],
        "수출중량 증감률 (%)": whole_metrics["weight_growth"],
        "kg당 금액 증감률 (%)": whole_metrics["unit_growth"],
    }
    frame = pd.DataFrame([total_row] + rows)
    part_rows = frame[frame["코드"] != "전체"].sort_values(
        "수출액 증감률 (%)",
        ascending=False,
    )
    ordered_frame = pd.concat(
        [frame[frame["코드"] == "전체"], part_rows],
        ignore_index=True,
    )
    melted = pd.melt(
        ordered_frame,
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
    st.caption("가운데 선 오른쪽 = 증가, 왼쪽 = 감소")
    zero_line = (
        alt.Chart(pd.DataFrame({"x": [0]})).mark_rule(color="#687583").encode(x="x:Q")
    )
    growth_chart = (
        alt.Chart(melted)
        .mark_bar()
        .encode(
            y=alt.Y(
                "부품:N",
                sort=ordered_frame["부품"].tolist(),
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
                "항목:N",
                alt.Tooltip("증감률:Q", format="+.1f"),
            ],
        )
    )
    st.altair_chart(growth_chart + zero_line, width="stretch")

    # 5. 표
    st.dataframe(
        ordered_frame.style.format(
            {
                "수출액 증감률 (%)": format_percent_value,
                "수출중량 증감률 (%)": format_percent_value,
                "kg당 금액 증감률 (%)": format_percent_value,
            },
            na_rep="—",
        ),
        hide_index=True,
        width="stretch",
    )
    st.caption("kg당 금액 = 수출액 ÷ 수출중량. 판매 가격이 아닌 대용치")
