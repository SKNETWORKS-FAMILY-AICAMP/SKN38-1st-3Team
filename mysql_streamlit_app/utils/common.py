"""여러 페이지가 함께 쓰는 코드: SQL 공통 조각, 공통 데이터 함수, 필터 줄, 증감률·흑자/적자 상태, 숫자 표시 형식.

기존 앱(SKN38-1st-3Team/utils/common.py)을 복사해 데이터 읽는 부분만 MySQL 쿼리로 바꿨다.
"""
import pandas as pd
import streamlit as st

from utils.constants import ALL_COUNTRIES, ALL_PARTS, ALL_PARTS_CODE, COUNTRIES, DEFAULT_START, NOTE, OTHERS, WORLD
from utils.db import query


# ---------- SQL 공통 조각 ----------
# 샘플(markets.py:45-46, 94-95)은 기타를 고르면 코드 목록으로 바꿔치기하려 했지만, 바꿀 글자가 이미 채워진 뒤라
# 걸리지 않았다. 여기서는 6개 코드를 CASE 로 「기타」 한 키로 묶어 거른다.
_OTHERS_SQL = ", ".join(f"'{c}'" for c in OTHERS)
PART_KEY = f"CASE WHEN t.hsCd IN ({_OTHERS_SQL}) THEN '기타' ELSE t.hsCd END"
PART_NAME = f"CASE WHEN t.hsCd IN ({_OTHERS_SQL}) THEN '기타' ELSE p.hsKor END"  # parts p 를 붙인 쿼리에서


def part_where(part: str) -> tuple[str, tuple]:
    """부품 선택 → (WHERE 조각, 값). 「자동차부품 전체」는 샘플처럼 합계 줄(hsCd 8708000000)을 읽는다."""
    if part == ALL_PARTS:
        return f"t.hsCd = '{ALL_PARTS_CODE}'", ()
    return f"{PART_KEY} = %s", (part,)


# ---------- 공통 데이터 함수 ----------

def get_months() -> list[str]:
    """기간 선택칸 달 목록 (2021.11 ~ 2026.09)."""
    return query("SELECT DISTINCT year FROM trades ORDER BY year")["year"].tolist()


def get_part_names() -> dict[str, str]:
    """부품 키 → 이름 (코드 순). 기타 6개 코드는 키 「기타」 하나."""
    t = query(f"""
        SELECT {PART_KEY} AS part_key, MAX({PART_NAME}) AS part_name
        FROM parts p JOIN (SELECT DISTINCT hsCd FROM trades) t ON t.hsCd = p.hsCd
        WHERE t.hsCd <> '{ALL_PARTS_CODE}'
        GROUP BY part_key
        ORDER BY MIN(t.hsCd)
    """)
    return dict(zip(t["part_key"], t["part_name"]))


def get_country_codes() -> dict[str, str]:
    """나라 이름 → 나라 코드 (데이터에 있는 10개국)."""
    t = query(f"""
        SELECT s.statKor, s.statCd
        FROM stats s
        WHERE s.statCd IN (SELECT DISTINCT statCd FROM trades WHERE statCd <> '{WORLD}')
    """)
    return dict(zip(t["statKor"], t["statCd"]))


def get_period_totals(f: dict) -> tuple[pd.Series, pd.Series]:
    """지표 카드용 (이번 기간 합계, 작년 같은 기간 합계). 열: exp_usd, imp_usd, balance, exp_kg.

    샘플 trend.py 의 query_select·query_past 를 한 쿼리로 합쳤다. 작년 자료가 없는 달은 0으로 더해진다.
    """
    where, wparams = part_where(f["part"])
    cols = {"exp_usd": "expDlr", "imp_usd": "impDlr", "balance": "balPayments", "exp_kg": "expwgt"}
    sums = [
        f"COALESCE(SUM(CASE WHEN t.year BETWEEN %s AND %s THEN t.{col} ELSE 0 END), 0) AS {tag}_{key}"
        for tag in ("cur", "prev") for key, col in cols.items()
    ]
    params = (f["start"], f["end"]) * 4 + (f["pstart"], f["pend"]) * 4 + (f["cc"],) + wparams
    row = query(f"SELECT {', '.join(sums)} FROM trades t WHERE t.statCd = %s AND {where}", params).iloc[0]
    cur = row.filter(like="cur_").rename(lambda k: k.removeprefix("cur_")).astype(float)
    prev = row.filter(like="prev_").rename(lambda k: k.removeprefix("prev_")).astype(float)
    return cur, prev


# ---------- 화면 공통 ----------

def header(section: str, title: str) -> None:
    st.caption(section)
    st.title(title)
    st.info(NOTE)


def filters(part: bool = False, country: bool = True) -> dict:
    """본문(제목 아래)의 기간·부품·상대국 선택을 한 줄로 그린다. 고른 값을 dict 로 돌려준다.

    cc 는 상대국 코드다. 「10개국 전체」면 샘플처럼 합계 줄(statCd "-")을 읽는다.
    """
    ms = get_months()
    cols = iter(st.columns(2 + part + country))
    start = next(cols).selectbox("기간 · 부터", ms, index=ms.index(DEFAULT_START) if DEFAULT_START in ms else 0, key="start")
    end = next(cols).selectbox("까지", ms, index=len(ms) - 1, key="end")
    f = {"start": start, "end": end, "part": ALL_PARTS, "country": ALL_COUNTRIES}
    if part:
        names = get_part_names()
        f["part"] = next(cols).selectbox(
            "부품", [ALL_PARTS, *names], key="part", format_func=lambda c: names.get(c, c)
        )
    if country:
        f["country"] = next(cols).selectbox("상대국", [ALL_COUNTRIES, *COUNTRIES], key="country")
    if start > end:
        st.error(f"기간 · 부터({start})가 까지({end})보다 늦습니다. 기간을 다시 고르세요.")
        st.stop()
    f["cc"] = WORLD if f["country"] == ALL_COUNTRIES else get_country_codes()[f["country"]]
    f["pstart"], f["pend"] = prev_range(start, end)
    # 작년 같은 기간 중 데이터 시작보다 앞선 달이 있는지. 그 달은 행이 없어서 0으로 더해진다.
    f["prev_partial"] = f["pstart"] < ms[0]
    f["first_month"] = ms[0]
    return f


def prev_range(start: str, end: str) -> tuple[str, str]:
    """작년 같은 기간 = 12개월 앞. 샘플은 11월~10월 묶음 5개 중 고정된 둘을 비교했다(trend.py:29-30)."""
    shift = lambda p: (pd.Period(p.replace(".", "-"), "M") - 12).strftime("%Y.%m")
    return shift(start), shift(end)


def pct(cur: float, prev: float | None) -> float | None:
    """증감률(%). 작년 값이 0이면 0으로 나눌 수 없어 None(화면에는 「작년 없음」)."""
    if prev is None or prev == 0:
        return None
    return (cur / prev - 1) * 100


def balance_status(cur: float, prev: float) -> str:
    if prev >= 0 and cur >= 0:
        return "흑자 확대" if cur > prev else "흑자 축소" if cur < prev else "흑자 유지"
    if prev < 0 and cur < 0:
        return "적자 확대" if cur < prev else "적자 축소" if cur > prev else "적자 유지"
    return "흑자 전환" if cur >= 0 else "적자 전환"


# ---------- 숫자 표시 ----------

def musd(x: float, digits: int = 0, sign: bool = False) -> str:
    """달러 → 백만 달러 글자."""
    return f"{x / 1e6:{'+' if sign else ''},.{digits}f}"


NO_PREV = "작년 없음"


def pct_text(p: float | None) -> str:
    return NO_PREV if p is None else f"{p:+.1f}%"


def yoy_text(p: float | None) -> str:
    return f"{NO_PREV} (작년 같은 기간 0)" if p is None else f"{p:+.1f}% (작년 같은 기간 대비)"


def period_text(f: dict) -> str:
    return f"{f['start']}–{f['end']}"


def prev_note(f: dict) -> None:
    if f["prev_partial"]:
        st.caption(f"작년 같은 기간({f['pstart']}–{f['pend']}) 중 데이터 시작({f['first_month']}) 이전 달은 0으로 계산했습니다.")
