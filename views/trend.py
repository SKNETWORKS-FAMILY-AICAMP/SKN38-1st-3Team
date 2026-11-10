# trend_page 화면
import altair as alt
import pandas as pd
import streamlit as st

from utils.common import (
    aggregate,
    format_country,
    format_number,
    period_filter_controls,
    growth,
    header,
    format_metric_value,
    format_signed_total,
    state,
)
from utils.constants import COUNTRIES, MONTHS
from utils.data import load_dashboard_data


MONTHS_PER_YEAR = 12
DISPLAY_MONTH_OFFSET = 22  # MONTHS의 첫 항목을 원본 월 인덱스에 맞춘 값
FIRST_AVAILABLE_MONTH_INDEX = 10  # 원본 데이터가 시작하는 2021년 11월 인덱스


def trend_page():
    # 1. 필터
    filters = period_filter_controls()
    start = filters["start"]
    end = filters["end"]
    header("01 전체 흐름", "자동차 부품 무역수지의 변화")
    (country_col,) = st.columns(1)
    with country_col:
        selected_country = st.selectbox(
            "대상 국가",
            ["10개국 전체"] + COUNTRIES,
            format_func=format_country,
            key="country",
        )
    country = "all" if selected_country == "10개국 전체" else selected_country

    # 2. 계산
    data = load_dashboard_data()
    current, previous = aggregate(start, end, country=country)
    export_sum = current["수출액"].sum()
    import_sum = current["수입액"].sum()
    previous_export_sum = previous["수출액"].sum()
    previous_import_sum = previous["수입액"].sum()
    balance = current["무역수지"].sum()
    unit = "$M"

    # 3. 지표 카드
    export_change = growth(export_sum, previous_export_sum)
    import_change = growth(import_sum, previous_import_sum)
    previous_balance = previous["무역수지"].sum()
    balance_change = balance - previous_balance
    export_delta = f"{format_metric_value(export_change)}% (작년 같은 기간 대비)"
    import_delta = f"{format_metric_value(import_change)}% (작년 같은 기간 대비)"
    balance_delta = (
        f"{format_metric_value(balance_change)} · {state(previous_balance, balance)}"
    )
    first, second, third = st.columns(3)
    first.metric(
        "수출액",
        f"{format_number(export_sum)} {unit}",
        export_delta,
        delta_color="normal",
        border=True,
    )
    second.metric(
        "수입액",
        f"{format_number(import_sum)} {unit}",
        import_delta,
        delta_color="normal",
        border=True,
    )
    third.metric(
        "무역수지",
        f"{format_signed_total(balance)} {unit}",
        balance_delta,
        delta_color="normal",
        border=True,
    )

    # 4. 차트
    st.subheader("월별 수출액과 수입액")
    st.caption(f"{unit} · 음영 = 선택한 기간")
    if country == "all":
        timeline = data
    else:
        timeline = data[data["나라"] == country]
    monthly = timeline.groupby(["k", "월"])[["수출액", "수입액"]].sum().reset_index()
    melted = pd.melt(
        monthly,
        id_vars=["k", "월"],
        value_vars=["수출액", "수입액"],
        var_name="구분",
        value_name="금액",
    )
    band_data = pd.DataFrame(
        {
            "시작": [start + DISPLAY_MONTH_OFFSET],
            "끝": [end + DISPLAY_MONTH_OFFSET],
        }
    )
    band = (
        alt.Chart(band_data)
        .mark_rect(opacity=0.12, color="#1d58b0")
        .encode(x="시작:Q", x2="끝:Q")
    )
    line = (
        alt.Chart(melted)
        .mark_line()
        .encode(
            x=alt.X(
                "k:Q",
                axis=alt.Axis(
                    title="연도",
                    # 월 인덱스의 12개월 간격을 연도 눈금으로 표시한다.
                    values=[0, 12, 24, 36, 48, 60],
                    labelExpr="datum.value/12+2021",
                ),
            ),
            y=alt.Y("금액:Q", title=unit),
            color=alt.Color(
                "구분:N",
                title="",
                scale=alt.Scale(
                    domain=["수출액", "수입액"],
                    range=["#1d58b0", "#c8620f"],
                ),
            ),
            tooltip=[
                "월:N",
                "구분:N",
                alt.Tooltip("금액:Q", format=",.1f"),
            ],
        )
    )
    st.altair_chart(line + band, width="stretch")

    st.subheader("해마다 같은 기간 무역수지")
    st.caption(f"{unit} · 무역수지 = 수출액 − 수입액")
    year_rows = []
    last_year = int(MONTHS[end][:4])
    for year in range(2022, last_year + 1):
        year_offset = MONTHS_PER_YEAR * (last_year - year)
        range_start = start + DISPLAY_MONTH_OFFSET - year_offset
        range_end = end + DISPLAY_MONTH_OFFSET - year_offset
        if range_start < FIRST_AVAILABLE_MONTH_INDEX:
            continue
        year_frame = data[(data["k"] >= range_start) & (data["k"] <= range_end)]
        if country != "all":
            year_frame = year_frame[year_frame["나라"] == country]
        yearly_balance = year_frame["무역수지"].sum()
        year_rows.append({"연도": str(year), "무역수지": yearly_balance})
    yearly_frame = pd.DataFrame(year_rows)
    bars = (
        alt.Chart(yearly_frame)
        .mark_bar()
        .encode(
            x=alt.X("연도:N", title=None),
            y=alt.Y("무역수지:Q", title=unit),
            color=alt.condition(
                "datum['무역수지'] >= 0",
                alt.value("#1b7f52"),
                alt.value("#be3f33"),
            ),
            tooltip=[
                "연도:N",
                alt.Tooltip("무역수지:Q", format=",.1f"),
            ],
        )
    )
    labels = (
        alt.Chart(yearly_frame)
        .mark_text(dy=-8)
        .encode(
            x="연도:N",
            y="무역수지:Q",
            text=alt.Text("무역수지:Q", format=",.0f"),
        )
    )
    st.altair_chart(bars + labels, width="stretch")
