import altair as alt
import pandas as pd
import streamlit as st

from utils.common import (
    aggregate,
    format_country,
    period_filter_controls,
    format_signed_value,
    header,
)
from utils.constants import COUNTRIES, MONTHS
from utils.parts_catalog import ITEMS
from utils.data import load_dashboard_data

EXPORT_COLOR = "#1d58b0"
IMPORT_COLOR = "#c8620f"


def country_shares(data, column):
    values = data.groupby("나라")[column].sum().reindex(COUNTRIES, fill_value=0)
    total = values.sum()
    if not total:
        return values * 0
    return values / total * 100


def markets_page():
    # 1. 필터
    filters = period_filter_controls()
    start = filters["start"]
    end = filters["end"]
    header("02 부품·시장", "어느 나라로 수출하고, 어느 나라에서 수입하나?")
    item_labels = {"자동차부품 전체": "all"}
    item_labels.update({f"{name} ({code})": code for code, name in ITEMS})
    item_col, measure_col = st.columns(2)
    with item_col:
        selected_item = st.selectbox("부품", list(item_labels), key="item")
    with measure_col:
        measure_name = st.selectbox("표시 기준", ["금액", "물량"], key="markets_measure")
    item_code = item_labels[selected_item]

    item_name = "자동차부품 전체"
    if item_code != "all":
        item_name = next(item[1] for item in ITEMS if item[0] == item_code)
    measures = (
        ("수출액", "수입액", "백만 달러")
        if measure_name == "금액"
        else ("수출중량", "수입중량", "톤")
    )
    export_column, import_column, unit = measures

    # 2. 기간 전체 비중과 시작·끝 월의 비중 변화 계산
    current, _ = aggregate(start, end, item_code=item_code)
    export_total = current[export_column].sum()
    import_total = current[import_column].sum()
    data = load_dashboard_data()
    if item_code != "all":
        data = data[data["부품 코드"] == item_code]
    start_data = data[data["월"] == MONTHS[start]]
    end_data = data[data["월"] == MONTHS[end]]
    start_export_shares = country_shares(start_data, export_column)
    end_export_shares = country_shares(end_data, export_column)
    start_import_shares = country_shares(start_data, import_column)
    end_import_shares = country_shares(end_data, import_column)
    rows = []
    for country in COUNTRIES:
        country_current = current[current["나라"] == country]
        export_value = country_current[export_column].sum()
        import_value = country_current[import_column].sum()
        export_share = export_value / export_total * 100 if export_total else 0
        import_share = import_value / import_total * 100 if import_total else 0
        rows.append(
            {
                "나라": country,
                "수출 비중 (%)": export_share,
                "수출 시작 비중 (%)": start_export_shares[country],
                "수출 끝 비중 (%)": end_export_shares[country],
                "수출 변화(%p)": end_export_shares[country] - start_export_shares[country],
                f"수출 ({unit})": export_value,
                "수입 비중 (%)": import_share,
                "수입 시작 비중 (%)": start_import_shares[country],
                "수입 끝 비중 (%)": end_import_shares[country],
                "수입 변화(%p)": end_import_shares[country] - start_import_shares[country],
                f"수입 ({unit})": import_value,
            }
        )

    frame = pd.DataFrame(rows)
    frame["나라 표시"] = frame["나라"].map(format_country)
    export_order = frame.sort_values("수출 비중 (%)", ascending=False)["나라 표시"].tolist()
    import_order = frame.sort_values("수입 비중 (%)", ascending=False)["나라 표시"].tolist()
    max_share = max(frame["수출 비중 (%)"].max(), frame["수입 비중 (%)"].max())
    share_domain = [0, max(10, min(100, max_share * 1.2))]
    frame["수출 비중 표시"] = frame["수출 비중 (%)"].map(lambda value: f"{value:.1f}%")
    frame["수입 비중 표시"] = frame["수입 비중 (%)"].map(lambda value: f"{value:.1f}%")
    frame["수출 변화 표시"] = frame["수출 변화(%p)"].map(
        lambda value: f"{format_signed_value(value)}%p"
    )
    frame["수입 변화 표시"] = frame["수입 변화(%p)"].map(
        lambda value: f"{format_signed_value(value)}%p"
    )

    st.caption(
        f"{item_name} · {MONTHS[start]}–{MONTHS[end]} · "
        f"기간 전체 비중은 10개국 합계 기준 · 변화는 "
        f"{MONTHS[start]} 대비 {MONTHS[end]} (%p)"
    )

    # 3. 1행: 수출·수입 비중을 내림차순으로 비교
    share_columns = st.columns(2)
    share_specs = [
        (
            share_columns[0],
            "수출",
            "수출 비중 (%)",
            "수출 비중 표시",
            export_order,
            EXPORT_COLOR,
        ),
        (
            share_columns[1],
            "수입",
            "수입 비중 (%)",
            "수입 비중 표시",
            import_order,
            IMPORT_COLOR,
        ),
    ]
    for column, title, share_column, label_column, order, color in share_specs:
        with column:
            st.subheader(f"{title} 비중")
            bars = (
                alt.Chart(frame)
                .mark_bar(color=color)
                .encode(
                    y=alt.Y("나라 표시:N", sort=order, title=None),
                    x=alt.X(
                        f"{share_column}:Q",
                        title="10개국 내 비중 (%)",
                        scale=alt.Scale(domain=share_domain),
                    ),
                    tooltip=[
                        "나라:N",
                        alt.Tooltip(
                            f"{share_column}:Q", format=".1f", title="비중 (%)"
                        ),
                        alt.Tooltip(
                            f"{title} ({unit}):Q",
                            format=",.1f",
                            title=f"거래 규모 ({unit})",
                        ),
                    ],
                )
            )
            labels = (
                alt.Chart(frame)
                .mark_text(align="left", dx=4, color="#333333")
                .encode(
                    y=alt.Y("나라 표시:N", sort=order, title=None),
                    x=alt.X(f"{share_column}:Q", scale=alt.Scale(domain=share_domain)),
                    text=alt.Text(f"{label_column}:N"),
                )
            )
            st.altair_chart((bars + labels).properties(height=340), width="stretch")

    # 4. 2행: 비중 그래프와 같은 순서·색으로 시작 월과 끝 월의 차이 표시
    change_columns = st.columns(2)
    change_specs = [
        (
            change_columns[0],
            "수출",
            "수출 변화(%p)",
            "수출 시작 비중 (%)",
            "수출 끝 비중 (%)",
            "수출 변화 표시",
            export_order,
            EXPORT_COLOR,
        ),
        (
            change_columns[1],
            "수입",
            "수입 변화(%p)",
            "수입 시작 비중 (%)",
            "수입 끝 비중 (%)",
            "수입 변화 표시",
            import_order,
            IMPORT_COLOR,
        ),
    ]
    for (
        column,
        title,
        change_column,
        start_column,
        end_column,
        label_column,
        order,
        color,
    ) in change_specs:
        with column:
            st.subheader(f"{title} 비중 변화")
            change_limit = max(1, frame[change_column].abs().max() * 1.35)
            change_chart = (
                alt.Chart(frame)
                .mark_bar()
                .encode(
                    y=alt.Y("나라 표시:N", sort=order, title=None),
                    x=alt.X(
                        f"{change_column}:Q",
                        title="비중 변화 (%p)",
                        scale=alt.Scale(domain=[-change_limit, change_limit]),
                    ),
                    color=alt.value(color),
                    tooltip=[
                        "나라:N",
                        alt.Tooltip(
                            f"{start_column}:Q",
                            format=".1f",
                            title=f"{MONTHS[start]} 비중 (%)",
                        ),
                        alt.Tooltip(
                            f"{end_column}:Q",
                            format=".1f",
                            title=f"{MONTHS[end]} 비중 (%)",
                        ),
                        alt.Tooltip(f"{change_column}:Q", format="+.1f", title="변화 (%p)"),
                    ],
                )
                .properties(height=330)
            )
            zero_line = (
                alt.Chart(pd.DataFrame({"기준": [0]}))
                .mark_rule(color="#444444", strokeWidth=1)
                .encode(
                    x=alt.X(
                        "기준:Q",
                        scale=alt.Scale(domain=[-change_limit, change_limit]),
                    )
                )
            )
            positive = frame[frame[change_column] >= 0]
            negative = frame[frame[change_column] < 0]
            positive_labels = (
                alt.Chart(positive)
                .mark_text(align="left", dx=4, color="#333333")
                .encode(
                    y=alt.Y("나라 표시:N", sort=order, title=None),
                    x=alt.X(
                        f"{change_column}:Q",
                        scale=alt.Scale(domain=[-change_limit, change_limit]),
                    ),
                    text=alt.Text(f"{label_column}:N"),
                )
            )
            negative_labels = (
                alt.Chart(negative)
                .mark_text(align="right", dx=-4, color="#333333")
                .encode(
                    y=alt.Y("나라 표시:N", sort=order, title=None),
                    x=alt.X(
                        f"{change_column}:Q",
                        scale=alt.Scale(domain=[-change_limit, change_limit]),
                    ),
                    text=alt.Text(f"{label_column}:N"),
                )
            )
            st.altair_chart(
                change_chart + zero_line + positive_labels + negative_labels,
                width="stretch",
            )

    # 5. 나라별 비중과 거래 규모 표
    table_columns = [
        "나라",
        "수출 비중 (%)",
        f"수출 ({unit})",
        "수출 변화(%p)",
        "수입 비중 (%)",
        f"수입 ({unit})",
        "수입 변화(%p)",
    ]
    table_frame = frame[table_columns].copy().round(1)
    st.dataframe(
        table_frame,
        hide_index=True,
        width="stretch",
        column_config={
            "수출 비중 (%)": st.column_config.NumberColumn(format="%.1f%%"),
            f"수출 ({unit})": st.column_config.NumberColumn(format="%,.1f"),
            "수출 변화(%p)": st.column_config.NumberColumn(format="%+.1f"),
            "수입 비중 (%)": st.column_config.NumberColumn(format="%.1f%%"),
            f"수입 ({unit})": st.column_config.NumberColumn(format="%,.1f"),
            "수입 변화(%p)": st.column_config.NumberColumn(format="%+.1f"),
        },
    )
