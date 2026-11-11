import pandas as pd
import streamlit as st

from utils.constants import DATA_FIRST_MONTH, COUNTRY_FLAGS, MONTHS, month_to_index
from utils.data import load_dashboard_data


# 입력 1234.5 -> 출력 "1,234.5"
def format_number(value, digits=None):
    if value is None or pd.isna(value):
        return "—"
    if digits is None:
        digits = 0 if abs(value) >= 100 else 1
    return f"{value:,.{digits}f}"


# 입력 -3.14 -> 출력 "−3.1"
def format_signed_value(value):
    if pd.isna(value):
        return "—"
    rounded_value = round(value, 1)
    if rounded_value == 0:
        return "0.0"
    sign = "+" if rounded_value > 0 else "−"
    return f"{sign}{abs(rounded_value):,.1f}"


# 입력 -3.14 -> 출력 "-3.1"
def format_metric_value(value):
    if value is None or pd.isna(value):
        return "—"
    rounded_value = round(value, 1)
    if rounded_value == 0:
        return "0.0"
    sign = "+" if rounded_value > 0 else "-"
    return f"{sign}{abs(rounded_value):,.1f}"


# 입력 3.14 -> 출력 "+3.1%"
def format_percent_value(value):
    if pd.isna(value):
        return "—"
    return f"{format_signed_value(value)}%"


def growth(now, before):
    if not before:
        return None
    return (now / before - 1) * 100


# 입력 -1234 -> 출력 "−1,234"
def format_signed_total(value):
    sign = "+" if value > 0 else "−" if value < 0 else ""
    return sign + format_number(abs(value))


def state(before, now):
    if before >= 0 and now < 0:
        return "적자 전환"
    if before < 0 and now >= 0:
        return "흑자 전환"
    if now >= 0:
        return "흑자 축소" if now < before else "흑자 확대"
    return "적자 확대" if now < before else "적자 축소"


def aggregate(start, end, item_code="all", country="all"):
    data = load_dashboard_data()
    start_k = month_to_index(MONTHS[start])
    end_k = month_to_index(MONTHS[end])
    current = data[(data["k"] >= start_k) & (data["k"] <= end_k)]
    first_data_k = month_to_index(DATA_FIRST_MONTH)
    if start_k - 12 < first_data_k:
        previous = data.iloc[0:0]
    else:
        previous = data[(data["k"] >= start_k - 12) & (data["k"] <= end_k - 12)]

    if item_code != "all":
        current = current[current["부품 코드"] == item_code]
        previous = previous[previous["부품 코드"] == item_code]
    if country != "all":
        current = current[current["나라"] == country]
        previous = previous[previous["나라"] == country]
    return current, previous


def header(eyebrow, question):
    st.caption(eyebrow)
    st.title(question)


def format_country(country):
    if country == "10개국 전체":
        return f"🌐 {country}"
    return f"{COUNTRY_FLAGS[country]} {country}"


def _normalize_period_selection():
    start = MONTHS.index(st.session_state["start"])
    end = MONTHS.index(st.session_state["end"])
    notice = ""

    if start > end:
        end = start
        notice = "시작 월이 끝 월보다 늦습니다."
    elif end - start > 11:
        end = min(start + 11, len(MONTHS) - 1)
        notice = (
            "설정할 수 있는 기간은 최대 12개월입니다."
        )

    st.session_state["end"] = MONTHS[end]
    st.session_state["period_filter_notice"] = notice


def period_filter_controls():
    st.session_state.setdefault("start", "2026.01")
    st.session_state.setdefault("end", "2026.09")
    if st.session_state["start"] not in MONTHS:
        st.session_state["start"] = MONTHS[0]
    if st.session_state["end"] not in MONTHS:
        st.session_state["end"] = MONTHS[-1]
    saved_start = MONTHS.index(st.session_state["start"])
    saved_end = MONTHS.index(st.session_state["end"])
    if saved_start > saved_end or saved_end - saved_start > 11:
        _normalize_period_selection()

    start_month = st.sidebar.selectbox(
        "기간 · 부터",
        MONTHS,
        key="start",
        on_change=_normalize_period_selection,
    )
    end_month = st.sidebar.selectbox(
        "까지",
        MONTHS,
        key="end",
        on_change=_normalize_period_selection,
    )
    start = MONTHS.index(start_month)
    end = MONTHS.index(end_month)
    notice = st.session_state.pop("period_filter_notice", "")
    if notice:
        st.sidebar.warning(notice)

    return {"start": start, "end": end}
