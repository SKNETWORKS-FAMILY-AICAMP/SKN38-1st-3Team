# 자동차부품(HS 8708) 무역 대시보드 — 로컬 MySQL 판

팀 샘플(`database_views_sample`) 방식으로 만든 Streamlit 앱이다. 실제 관세청 데이터(CSV)를 로컬 MySQL `mysql_streamlit_app` 에 넣고, 계산은 각 페이지 파일 안의 SQL이 MySQL에서 한다. 메뉴 5개는 저장소 맨 위 앱과 같다. 로컬 MySQL 에 접속하므로 실행한 PC에서만 돈다(Streamlit Cloud 배포 불가).

## 처음 한 번: 준비와 DB 만들기

MySQL 8.0 이상이 필요하다. PowerShell 에서 이 폴더(`mysql_streamlit_app`)로 들어가 실행한다.

```powershell
python -m venv .venv                         # 이미 있으면 건너뛴다
.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:DB_PASSWORD = "비밀번호"                   # MySQL root 비밀번호. 파일에 적지 않는다
.venv\Scripts\python.exe database\build_db.py
```

끝에 `mysql_streamlit_app: parts 26, stats 213, trades 14045 (CSV 11924 + 부품 전체 590 + 전세계 1531)` 가 나오면 된다. 다시 실행하면 테이블을 지우고 처음부터 다시 만든다.

## 실행

```powershell
$env:DB_PASSWORD = "비밀번호"
.venv\Scripts\streamlit run app.py
```

브라우저 왼쪽 메뉴 아래에 「데이터: MySQL mysql_streamlit_app」이 보이면 된다. 비밀번호가 없거나 틀리면, 또는 MySQL 이 꺼져 있으면 화면에 오류 문구가 뜨고 멈춘다. DB를 고친 뒤에는 앱을 다시 켜야 새 숫자가 나온다(결과를 캐시한다).

접속 값 이름은 저장소 맨 위 `.env.example` 과 같다. 주소·포트·사용자·DB 이름이 다르면 `DB_HOST`·`DB_PORT`·`DB_USER`·`DB_NAME` 을 준다(기본 127.0.0.1·3306·root·mysql_streamlit_app). `build_db.py` 는 `DB_NAME` 을 읽지 않고 언제나 `mysql_streamlit_app` 만 만든다(다른 DB의 테이블을 지우지 않게).

## 페이지와 함수

각 페이지 파일에 DB 쿼리로 데이터를 받아오는 함수(`get_…`)와 화면을 그리는 함수(`show_…`)가 있다. `app.py` 는 그리는 함수만 부른다.

| 메뉴 | 파일 | 데이터 함수 | 그리는 함수 |
|---|---|---|---|
| 전체 흐름 | `views/trend.py` | `get_monthly`, `get_yearly_balance`, (`common.get_period_totals`) | `show_trend` |
| 부품별 무역수지 | `views/parts.py` | `get_parts_balance` | `show_parts` |
| 나라별 비중 | `views/markets.py` | `get_country_share` | `show_markets` |
| 금액과 중량 | `views/volume.py` | `get_part_growth`, (`common.get_period_totals`) | `show_volume` |
| 부품 코드 안내 | `views/codes.py` | `get_codes` | `show_codes` |

필터 줄(기간·상대국·부품)과 여러 페이지가 쓰는 데이터 함수(달 목록, 부품 이름, 나라 코드, 기간 합계)는 `utils/common.py` 에 있다.

## 계산 기준

- 「10개국 전체」는 전세계 합계 줄(statCd `-`), 「자동차부품 전체」는 부품 전체 합계 줄(hsCd `8708000000`)을 읽는다. 나라별·부품별 목록에서는 이 합계 줄을 뺀다.
- 작년 같은 기간 = 고른 기간을 12개월 앞으로 옮긴 기간. 데이터가 없는 달은 0. 작년 값이 0이면 증감률은 「작년 없음」.
- 작은 부품 코드 6개(8708959000, 8708991010–8708991050)는 「기타」 한 줄로 묶는다. 부품 코드 안내에는 25개를 모두 보인다.
- 샘플 코드에서 고친 곳: trend.py 접속 줄 문법 오류, markets.py 의 ×200(합계 줄을 빼고 ×100), 기타 묶음이 걸리지 않던 것, 작년 대비를 줄 순서로 빼던 것. 자세한 내용은 각 파일 맨 위 설명.

## 폴더 구조

```
├ app.py            # 페이지 설정, 메뉴, show_… 호출
├ requirements.txt  # streamlit, pandas, altair, mysql-connector-python
├ database/
│ ├ build_db.py     # DB 만들기 (아래 SQL 실행 → CSV 넣기 → 엑셀 이름 → 합계 줄)
│ ├ Create_hs8708_tables.sql, Load_parts_data.sql, Load_stats_data.sql, Load_World_trades_data.sql  # 팀 샘플 그대로
│ └ hs8708_10countries.csv  # 6번 엑셀에서 뽑은 데이터 (10월이 2022.10 으로 맞게 들어 있다)
├ views/            # 페이지당 한 파일: get_… + show_…
└ utils/
  ├ db.py           # MySQL 접속(DB_PASSWORD)과 query()
  ├ common.py       # SQL 공통 조각, 공통 데이터 함수, 필터 줄, 숫자 표시
  └ constants.py    # DB 이름, 합계 줄 코드, 나라 목록, 색, 용어
```
