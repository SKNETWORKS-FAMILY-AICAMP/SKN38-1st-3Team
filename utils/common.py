import pandas as pd
import streamlit as st

from utils.constants import COUNTRIES, ITEMS, MONTHS
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
    start_k = start + 22
    end_k = end + 22
    current = data[(data["k"] >= start_k) & (data["k"] <= end_k)]
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


def filter_controls(use_item=False, use_country=False):
    start_month = st.sidebar.selectbox(
        "기간 · 부터", MONTHS, index=MONTHS.index("2026.01"), key="start"
    )
    end_month = st.sidebar.selectbox(
        "까지", MONTHS, index=MONTHS.index("2026.09"), key="end"
    )
    start = MONTHS.index(start_month)
    end = MONTHS.index(end_month)
    notice = ""

    if start > end:
        end = start
        notice = "시작 월이 끝 월보다 늦어 끝 월을 시작 월로 맞췄습니다."
    if end - start > 11:
        end = start + 11
        notice = (
            "기간은 최대 12개월입니다. 끝 월을 시작 월부터 "
            "12개월째로 조정했습니다."
        )
    if notice:
        st.sidebar.warning(notice)

    item_code = "all"
    country = "all"
    if use_item:
        item_labels = {"자동차부품 전체": "all"}
        item_labels.update(
            {f"{name} ({code})": code for code, name in ITEMS}
        )
        selected_item = st.sidebar.selectbox("부품", list(item_labels), key="item")
        item_code = item_labels[selected_item]
    if use_country:
        selected_country = st.sidebar.selectbox(
            "상대국", ["10개국 전체"] + COUNTRIES, key="country"
        )
        if selected_country != "10개국 전체":
            country = selected_country

    return {
        "start": start,
        "end": end,
        "item_code": item_code,
        "country": country,
    }
