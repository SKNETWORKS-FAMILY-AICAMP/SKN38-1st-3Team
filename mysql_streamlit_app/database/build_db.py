"""MySQL 에 mysql_streamlit_app 데이터베이스를 처음부터 만든다.

실행 (sample_1110 폴더에서):
    $env:DB_PASSWORD = "비밀번호"
    .venv\\Scripts\\python.exe database\\build_db.py

순서 (팀 샘플의 DBeaver 순서와 같다):
1. CREATE DATABASE mysql_streamlit_app (없으면)
2. Create_hs8708_tables.sql  — 테이블 3개를 지우고 다시 만든다
3. Load_parts_data.sql, Load_stats_data.sql — 부품 코드·나라 코드
4. hs8708_10countries.csv → trades (11,924행)
   서버가 local_infile=0 이라 LOAD DATA LOCAL 을 못 써서 INSERT 로 넣는다.
5. 화면 이름을 엑셀 이름으로 덮어쓴다 — parts.hsKor·hsExp(부품 25개), stats.statKor(나라 10개)
   샘플 이름은 엑셀과 부품 18개, 나라 2개(체코·우즈벡)가 달라서 화면 이름이 기존 앱과 어긋난다.
6. Load_World_trades_data.sql — 합계 줄(부품 전체 hsCd 8708000000, 전세계 statCd "-")
7. 개수 확인: trades 14,045 = 11,924 + 590 + 1,531

다시 실행해도 같은 결과가 나온다(2단계에서 테이블을 지우고 다시 만든다).
"""
import csv
import os
import re
import sys
from pathlib import Path

import mysql.connector

HERE = Path(__file__).resolve().parent
# 환경 변수 DB_NAME 은 일부러 읽지 않는다. 2단계가 테이블을 지우고 다시 만들기 때문에,
# 다른 DB(예: 팀 DB)를 가리킨 채 실행하면 그 DB 의 trades·parts·stats 가 지워진다.
DB_NAME = "mysql_streamlit_app"
CSV_PATH = HERE / "hs8708_10countries.csv"


def run_sql_file(cur, name: str) -> None:
    text = (HERE / name).read_text(encoding="utf-8")
    text = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--"))
    # 문장 끝(줄 끝의 ;)으로 나눈다. 샘플 파일의 이름 글자 안에는 ; 가 없다.
    for stmt in re.split(r";\s*(?:\n|$)", text):
        if stmt.strip():
            cur.execute(stmt)


def num(x: str) -> float | None:
    return None if x.strip() == "" else float(x)


def main() -> None:
    pwd = os.environ.get("DB_PASSWORD")
    if not pwd:
        sys.exit("환경 변수 DB_PASSWORD 에 MySQL 비밀번호를 넣고 다시 실행하세요.")
    conn = mysql.connector.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT") or 3306),
        user=os.environ.get("DB_USER", "root"),
        password=pwd,
        charset="utf8mb4",
    )
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{DB_NAME}` CHARACTER SET utf8mb4")
    cur.execute(f"USE `{DB_NAME}`")

    run_sql_file(cur, "Create_hs8708_tables.sql")
    run_sql_file(cur, "Load_parts_data.sql")
    run_sql_file(cur, "Load_stats_data.sql")

    with open(CSV_PATH, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    cur.executemany(
        "INSERT INTO trades (year, hsCd, statCd, expDlr, expwgt, impDlr, impwgt, balPayments) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        [(r["year"], r["hsCd"], r["statCd"], num(r["expDlr"]), num(r["expWgt"]), num(r["impDlr"]),
          num(r["impWgt"]), num(r["balPayments"])) for r in rows],
    )

    parts = {r["hsCd"]: (r["hsNameKor"], r["statKor"]) for r in rows}  # statKor 열에 부품 원문 이름이 들어 있다
    cur.executemany("UPDATE parts SET hsKor = %s, hsExp = %s WHERE hsCd = %s",
                    [(short, full, code) for code, (short, full) in parts.items()])
    countries = {r["statCd"]: r["statCdCntnKor1"] for r in rows}
    cur.executemany("UPDATE stats SET statKor = %s WHERE statCd = %s",
                    [(name, code) for code, name in countries.items()])

    run_sql_file(cur, "Load_World_trades_data.sql")
    conn.commit()

    cur.execute("SELECT COUNT(*), SUM(hsCd = '8708000000' AND statCd <> '-'), SUM(statCd = '-') FROM trades")
    total, part_all, world = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM parts")
    n_parts = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM stats")
    n_stats = cur.fetchone()[0]
    print(f"{DB_NAME}: parts {n_parts}, stats {n_stats}, trades {total} "
          f"(CSV {len(rows)} + 부품 전체 {int(part_all)} + 전세계 {int(world)})")
    conn.close()


if __name__ == "__main__":
    main()
