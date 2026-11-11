import altair as alt
import pandas as pd
import streamlit as st

from utils.common import (
    aggregate,
    format_number,
    format_percent_value,
    format_signed_value,
    growth,
    header,
    period_filter_controls,
)
from utils.constants import MONTHS, month_to_index
from utils.parts_catalog import ITEMS

PART_COLORS = [
    "#1d58b0",
    "#c8620f",
    "#1b7f52",
    "#8e44ad",
    "#be3f33",
    "#00838f",
    "#8c6d31",
    "#6f4e7c",
    "#7f7f7f",
    "#a55194",
    "#31a354",
    "#3182bd",
    "#e6550d",
    "#756bb1",
    "#636363",
    "#e377c2",
    "#17becf",
    "#bcbd22",
    "#9467bd",
    "#8c564b",
    "#393b79",
]


def format_amount(value):
    return format_number(value, 1)


def _part_chart(
    frame,
    metric,
    title,
    unit,
    part_order,
    part_colors,
    months,
    shared_domain=None,
    show_zero=False,
):
    value_axis = alt.Axis(tickCount=5, format=",.0f")
    value_scale = alt.Scale(domain=shared_domain) if shared_domain else alt.Undefined
    chart = (
        alt.Chart(frame)
        .mark_line(point=True)
        .encode(
            x=alt.X("월:N", sort=months, title=None),
            y=alt.Y(
                f"{metric}:Q",
                title=unit,
                axis=value_axis,
                scale=value_scale,
            ),
            color=alt.Color(
                "비교 대상:N",
                scale=alt.Scale(domain=part_order, range=part_colors),
                legend=None,
            ),
            detail="비교 대상:N",
            tooltip=[
                alt.Tooltip("비교 대상:N", title="부품"),
                alt.Tooltip("월:N", title="월"),
                alt.Tooltip(f"{metric}:Q", title=title, format=",.1f"),
            ],
        )
        .properties(height=320)
    )
    if show_zero:
        zero_line = (
            alt.Chart(pd.DataFrame({metric: [0]}))
            .mark_rule(color="#687583")
            .encode(y=alt.Y(f"{metric}:Q", axis=value_axis))
        )
        chart = zero_line + chart
    return chart


def parts_page():
    # 1. 필터
    filters = period_filter_controls()
    start = filters["start"]
    end = filters["end"]
    header("02 부품·시장", "부품별 무역수지 변화")

    item_labels = {"자동차부품 전체 (합계)": "all"}
    item_labels.update({f"{name} ({code})": code for code, name in ITEMS})
    part_color_map = {
        label: PART_COLORS[index % len(PART_COLORS)]
        for index, label in enumerate(item_labels)
    }
    filter_columns = st.columns(2)
    with filter_columns[0]:
        selected_items = st.multiselect(
            "비교할 부품",
            list(item_labels),
            default=["자동차부품 전체 (합계)"],
            key="parts_items",
        )
    with filter_columns[1]:
        measure_name = st.selectbox(
            "표시 기준",
            ["금액", "물량"],
            key="parts_measure",
        )

    if not selected_items:
        st.info("비교할 부품을 하나 이상 선택해 주세요.")
        return

    st.sidebar.markdown("#### 그래프 범례")
    for item in selected_items:
        color = part_color_map[item]
        st.sidebar.markdown(
            f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;">'
            f'<span style="width:10px;height:10px;border-radius:50%;'
            f'background:{color};display:inline-block;flex:none;"></span>{item}</div>',
            unsafe_allow_html=True,
        )

    if measure_name == "금액":
        export_metric = "수출액"
        import_metric = "수입액"
        export_title = "수출액"
        import_title = "수입액"
        balance_title = "무역수지"
        unit = "백만 달러"
        show_balance = True
    else:
        export_metric = "수출중량"
        import_metric = "수입중량"
        export_title = "수출중량"
        import_title = "수입중량"
        unit = "톤"
        show_balance = False

    # 2. 선택 부품별 월간 추이와 기간 합계 계산
    chart_rows = []
    table_rows = []
    part_order = []
    for selected_item in selected_items:
        item_code = item_labels[selected_item]
        current, previous = aggregate(start, end, item_code=item_code)
        if item_code == "all":
            current_name = "자동차부품 전체 (합계)"
            code = "전체"
        else:
            current_name = selected_item
            code = item_code

        monthly_metrics = [export_metric, import_metric]
        if show_balance:
            monthly_metrics.append("무역수지")
        monthly = current.groupby("k")[monthly_metrics].sum()
        for month_index in range(start, end + 1):
            month = MONTHS[month_index]
            month_key = month_to_index(month)
            month_values = (
                monthly.loc[month_key] if month_key in monthly.index else None
            )
            export_value = (
                month_values[export_metric] if month_values is not None else 0
            )
            import_value = (
                month_values[import_metric] if month_values is not None else 0
            )
            chart_row = {
                "월": month,
                "비교 대상": current_name,
                export_title: export_value,
                import_title: import_value,
            }
            if show_balance:
                chart_row[balance_title] = (
                    month_values["무역수지"] if month_values is not None else 0
                )
            chart_rows.append(chart_row)

        export_sum = current[export_metric].sum()
        import_sum = current[import_metric].sum()
        previous_export_sum = previous[export_metric].sum() if not previous.empty else None
        previous_import_sum = previous[import_metric].sum() if not previous.empty else None
        table_row = {
            "부품": current_name,
            "코드": code,
            f"{export_title} ({unit})": export_sum,
            f"{export_title} 차이 ({unit})": (
                export_sum - previous_export_sum if previous_export_sum is not None else None
            ),
            f"{export_title} 변화 (%)": growth(export_sum, previous_export_sum),
            f"{import_title} ({unit})": import_sum,
            f"{import_title} 차이 ({unit})": (
                import_sum - previous_import_sum if previous_import_sum is not None else None
            ),
            f"{import_title} 변화 (%)": growth(import_sum, previous_import_sum),
        }
        if show_balance:
            balance_sum = current["무역수지"].sum()
            previous_balance_sum = (
                previous["무역수지"].sum() if not previous.empty else None
            )
            table_row[f"{balance_title} ({unit})"] = balance_sum
            table_row[f"{balance_title} 차이 ({unit})"] = (
                balance_sum - previous_balance_sum
                if previous_balance_sum is not None
                else None
            )
        table_rows.append(table_row)
        part_order.append(current_name)

    chart_frame = pd.DataFrame(chart_rows)
    table_frame = pd.DataFrame(table_rows)
    months = MONTHS[start : end + 1]
    part_colors = [part_color_map[item] for item in selected_items]
    st.caption(
        f"{MONTHS[start]}–{MONTHS[end]} · 10개국 전체 · {unit} · "
        "변화는 작년 같은 기간 대비"
    )

    # 3. 월별 그래프
    export_max = chart_frame[export_title].max()
    import_max = chart_frame[import_title].max()
    shared_max = max(export_max, import_max)
    shared_domain = [0, shared_max * 1.1 if shared_max > 0 else 1]
    chart_specs = [
        (export_title, export_title, False),
        (import_title, import_title, False),
    ]
    if show_balance:
        chart_specs.append((balance_title, balance_title, True))
    chart_columns = st.columns(len(chart_specs))
    for column, (metric, title, show_zero) in zip(chart_columns, chart_specs):
        with column:
            st.subheader(title)
            st.altair_chart(
                _part_chart(
                    chart_frame,
                    metric,
                    title,
                    unit,
                    part_order,
                    part_colors,
                    months,
                    shared_domain=None if show_zero else shared_domain,
                    show_zero=show_zero,
                ),
                width="stretch",
            )

    # 4. 선택 기간 합계와 작년 같은 기간 대비 변화 표
    st.subheader("기간 합계와 작년 같은 기간 대비 변화")
    table_formats = {
        f"{export_title} ({unit})": format_amount,
        f"{export_title} 차이 ({unit})": format_signed_value,
        f"{export_title} 변화 (%)": format_percent_value,
        f"{import_title} ({unit})": format_amount,
        f"{import_title} 차이 ({unit})": format_signed_value,
        f"{import_title} 변화 (%)": format_percent_value,
    }
    if show_balance:
        table_formats[f"{balance_title} ({unit})"] = format_signed_value
        table_formats[f"{balance_title} 차이 ({unit})"] = format_signed_value
    st.dataframe(
        table_frame.style.format(table_formats),
        hide_index=True,
        width="stretch",
    )
