"""실제 데이터로 바꿀 때는 load_parts, load_stats, load_trades만 교체한다.

연결 정보를 코드에 쓰지 말고 st.secrets를 사용한다.
확인된 단위: expDlr, impDlr는 달러이며 expwgt, impwgt는 kg이다.
statCd는 US 같은 2자리 코드다. year는 원본과 같은 YYYY.MM 형식이다.
가상 자료는 2021.11~2026.09의 25개 코드와 고정 10개국을 사용한다.
hsExp와 statEng는 원본 데이터에 없으며 화면에서 사용하지 않는다.
"""
import math

import pandas as pd
import streamlit as st

from utils.constants import (
    COUNTRY_CODES,
    COUNTRY_ENGLISH,
    ITEMS,
    PART_DESCRIPTIONS,
    PART_NAMES,
)

# 1. 가상 데이터 설정
# 금액은 백만 달러, 중량은 톤 단위로 된 기존 계수를 보관한다.
_PART_COEFFICIENTS = {
    "8708100000": (420, 250, 0.02, 0.06, 5.7, 0.02),
    "8708210000": (120, 160, 0.02, 0.03, 13, 0.01),
    "8708220000": (225, 75, 0.04, 0.03, 6.5, 0.02),
    "8708290000": (1500, 500, 0.03, 0.03, 6, 0.02),
    "8708301000": (275, 112, 0.06, 0.04, 8.2, 0.02),
    "8708302000": (220, 90, 0.06, 0.04, 8.2, 0.02),
    "8708303000": (220, 90, 0.06, 0.04, 8.2, 0.02),
    "8708309000": (385, 158, 0.06, 0.04, 8.2, 0.02),
    "8708400000": (1300, 1085, 0.04, 0.077, 12.5, 0.04),
    "8708501000": (490, 210, 0.04, 0.03, 7.5, 0.01),
    "8708502000": (210, 90, 0.04, 0.03, 7.5, 0.01),
    "8708700000": (600, 350, -0.03, 0.04, 6.8, -0.01),
    "8708800000": (900, 380, 0.07, 0.03, 9.4, 0.01),
    "8708910000": (300, 180, 0.02, 0.02, 7, 0.01),
    "8708920000": (200, 140, 0.01, 0.02, 5.5, 0.01),
    "8708930000": (220, 160, -0.02, 0.03, 9, 0),
    "8708940000": (800, 420, 0.05, 0.05, 11, 0.03),
    "8708951000": (300, 330, 0.03, 0.06, 14, 0.02),
    "8708999000": (2400, 675, 0.05, 0.04, 9, 0.02),
    "기타": (800, 225, 0.02, 0.04, 9, 0.02),
}
_OTHER_HS_CODES = [
    "8708959000",
    "8708991010",
    "8708991020",
    "8708991030",
    "8708991040",
    "8708991050",
]
_STAT_CODES = [
    "US",
    "CN",
    "MX",
    "SK",
    "CZ",
    "IN",
    "UZ",
    "JP",
    "DE",
    "VN",
]
_EXPORT_WEIGHTS = [0.30, 0.09, 0.08, 0.07, 0.05, 0.05, 0.03, 0.03, 0.04, 0.03]
_EXPORT_DRIFT = [-0.02, -0.03, 0.04, 0.01, 0, 0.03, 0.02, 0, 0, 0.03]
_IMPORT_WEIGHTS = [0.10, 0.36, 0.04, 0.01, 0.02, 0.03, 0.01, 0.17, 0.13, 0.06]
_IMPORT_DRIFT = [0, 0.03, 0, 0, 0, 0.02, 0, -0.02, -0.01, 0.04, 0]
_MONTH_SHARES = [
    0.075,
    0.07,
    0.085,
    0.085,
    0.083,
    0.087,
    0.08,
    0.078,
    0.085,
    0.09,
    0.088,
    0.094,
]

# 2. ERD 원본 표 불러오기
@st.cache_data
def load_parts():
    official_names = {
        "8708100000": "완충기와 그 부분품",
        "8708210000": "안전벨트",
        "8708220000": "전방 윈드스크린, 후방 창문과 그 밖의 창문",
        "8708290000": "기타(8708.29)",
        "8708301000": "장착된 브레이크 라이닝",
        "8708302000": "브레이크 부스터",
        "8708303000": "전자 제어식 제동장치",
        "8708309000": "기타(8708.30)",
        "8708400000": "기어박스와 그 부분품",
        "8708501000": "차동장치를 갖춘 구동 차축과 그 부분품",
        "8708502000": "비구동 차축과 그 부분품",
        "8708700000": "로드 휠과 그 부분품ㆍ부속품",
        "8708800000": "서스펜션 시스템과 그 부분품",
        "8708910000": "방열기와 그 부분품",
        "8708920000": "소음기(머플러), 배기관, 그 부분품",
        "8708930000": "클러치와 그 부분품",
        "8708940000": "운전대ㆍ스티어링칼럼ㆍ운전박스와 그 부분품",
        "8708951000": "에어백",
        "8708959000": "기타(8708.95)",
        "8708991010": "제8701호의 것",
        "8708991020": "제8702호의 것",
        "8708991030": "제8703호의 것",
        "8708991040": "제8704호의 것",
        "8708991050": "제8705호의 것",
        "8708999000": "기타(8708.99)",
    }
    rows = []
    for code, official_name in official_names.items():
        rows.append({"hsCd": code, "hsKor": official_name, "hsExp": ""})
    return pd.DataFrame(rows, columns=["hsCd", "hsKor", "hsExp"])


@st.cache_data
def load_stats():
    rows = []
    for stat_code in _STAT_CODES:
        rows.append(
            {
                "statCd": stat_code,
                "statKor": COUNTRY_CODES[stat_code],
                "statEng": COUNTRY_ENGLISH[stat_code],
            }
        )
    return pd.DataFrame(rows, columns=["statCd", "statKor", "statEng"])


@st.cache_data
def load_trades():
    rows = []
    monthly_base = [share * 12 for share in _MONTH_SHARES]

    for item_index, (item_code, _) in enumerate(ITEMS):
        (
            annual_export,
            annual_import,
            export_growth,
            import_growth,
            unit_value,
            value_growth,
        ) = _PART_COEFFICIENTS[item_code]
        for month_index in range(10, 69):
            year_fraction = month_index / 12
            month_number = month_index % 12
            year_number = 2021 + month_index // 12

            export_share_values = []
            import_share_values = []
            for country_index in range(len(_STAT_CODES)):
                export_share = _EXPORT_WEIGHTS[country_index]
                import_share = _IMPORT_WEIGHTS[country_index]
                export_share *= 1 + 0.55 * math.sin(
                    item_index * 1.7 + country_index * 2.3
                )
                export_share *= (
                    1 + _EXPORT_DRIFT[country_index] * year_fraction * 2
                )
                import_share *= 1 + 0.5 * math.sin(
                    (item_index + 3) * 1.7 + country_index * 2.3
                )
                import_share *= (
                    1 + _IMPORT_DRIFT[country_index] * year_fraction * 2
                )
                export_share_values.append(export_share)
                import_share_values.append(import_share)

            export_total = sum(export_share_values)
            import_total = sum(import_share_values)
            export_shares = [value / export_total for value in export_share_values]
            import_shares = [value / import_total for value in import_share_values]
            export_season = monthly_base[month_number] * (
                1 + 0.03 * math.sin(month_index * 0.7 + item_index)
            )
            import_season = monthly_base[(month_number + 1) % 12] * (
                1 + 0.03 * math.cos(month_index * 0.5 + item_index)
            )
            export_event = 0.88 if 27 <= month_index <= 29 else 1
            import_event = (
                1.25
                if item_code == "8708400000" and month_index == 46
                else 1
            )
            gear_shift = (
                1.04 if item_code == "8708400000" and year_number == 2026 else 1
            )
            part_split = 1
            if item_code == "8708220000" and month_index < 12:
                part_split = 0
            elif item_code == "8708290000" and month_index >= 12:
                part_split = 0.85



            for country_index, stat_code in enumerate(_STAT_CODES):
                export = (
                    annual_export
                    / 12
                    * (1 + export_growth) ** year_fraction
                    * export_season
                    * export_event
                    * part_split
                    * export_shares[country_index]
                    * (
                        1
                        + 0.05
                        * math.sin(
                            month_index * 0.37
                            + item_index * 2
                            + country_index
                        )
                    )
                )
                import_amount = (
                    annual_import
                    / 12
                    * (1 + import_growth) ** year_fraction
                    * import_season
                    * import_event
                    * gear_shift
                    * part_split
                    * import_shares[country_index]
                    * (
                        1
                        + 0.05
                        * math.cos(
                            month_index * 0.29
                            + item_index
                            + country_index * 1.7
                        )
                    )
                )
                export_weight_tons = (
                    export
                    * 1e6
                    / (
                        unit_value
                        * (1 + value_growth * year_fraction)
                        * (
                            1
                            + 0.025
                            * math.sin(
                                item_index + country_index + month_index * 0.3
                            )
                        )
                    )
                    / 1000
                )
                import_weight_tons = import_amount * 1e6 / (unit_value * 1.1) / 1000
                part_codes = (
                    _OTHER_HS_CODES if item_code == "기타" else [item_code]
                )
                for part_code in part_codes:
                    if item_code == "8708220000" and month_index < 12:
                        continue
                    if part_code == "8708991010" and stat_code == "UZ":
                        continue
                    split_count = len(part_codes)
                    export_dollars = export * 1e6 / split_count
                    import_dollars = import_amount * 1e6 / split_count
                    export_weight_kg = export_weight_tons * 1000 / split_count
                    import_weight_kg = import_weight_tons * 1000 / split_count
                    rows.append(
                        {
                            "year": f"{year_number}.{month_number + 1:02d}",
                            "statCd": stat_code,
                            "hsCd": part_code,
                            "expDlr": export_dollars,
                            "expwgt": export_weight_kg,
                            "impDlr": import_dollars,
                            "impwgt": import_weight_kg,
                            "balPayments": export_dollars - import_dollars,
                        }
                    )
    return pd.DataFrame(
        rows,
        columns=[
            "year",
            "statCd",
            "hsCd",
            "expDlr",
            "expwgt",
            "impDlr",
            "impwgt",
            "balPayments",
        ],
    )


# 3. 화면에서 쓰는 표로 바꾸기
@st.cache_data
def load_dashboard_data():
    trades_frame = load_trades()
    parts_frame = load_parts()
    stats_frame = load_stats()
    joined = pd.merge(trades_frame, parts_frame, on="hsCd", how="left")
    joined = pd.merge(joined, stats_frame, on="statCd", how="left")

    named_codes = [code for code, name in ITEMS if code != "기타"]
    joined["부품 코드"] = joined["hsCd"].where(
        joined["hsCd"].isin(named_codes),
        "기타",
    )
    joined["부품"] = joined["부품 코드"].map(PART_NAMES)
    joined["부품 설명"] = joined["부품 코드"].map(PART_DESCRIPTIONS)
    joined["나라"] = joined["statKor"]
    joined["월"] = joined["year"]
    year_parts = joined["year"].str.split(".", expand=True)
    joined["k"] = (year_parts[0].astype(int) - 2021) * 12
    joined["k"] += year_parts[1].astype(int) - 1
    joined["수출액"] = joined["expDlr"] / 1_000_000
    joined["수입액"] = joined["impDlr"] / 1_000_000
    joined["수출중량"] = joined["expwgt"] / 1_000
    joined["수입중량"] = joined["impwgt"] / 1_000
    joined["무역수지"] = joined["balPayments"] / 1_000_000
    joined["원본 HS코드"] = joined["hsCd"]
    joined["공식 품명"] = joined["hsKor"]

    dashboard_columns = [
        "월",
        "k",
        "부품 코드",
        "부품",
        "부품 설명",
        "나라",
        "원본 HS코드",
        "공식 품명",
        "수출액",
        "수입액",
        "수출중량",
        "수입중량",
        "무역수지",
    ]
    dashboard_frame = joined[dashboard_columns]
    dashboard_frame = dashboard_frame.groupby(
        [
            "월",
            "k",
            "부품 코드",
            "부품",
            "부품 설명",
            "나라",
            "원본 HS코드",
            "공식 품명",
        ],
        as_index=False,
        sort=False,
    ).sum()
    return dashboard_frame
