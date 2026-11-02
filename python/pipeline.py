"""Load the raw CSVs into SQLite, build staging and marts, run the data tests, write results.json.

Run: python3 python/pipeline.py   (after generate_data.py)
"""
import csv
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"
DB = OUT / "desk.db"


def typed(v):
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            pass
    return v


def load(con):
    for path in sorted(RAW.glob("*.csv")):
        table = "raw_" + path.stem
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        header, body = rows[0], rows[1:]
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(f"CREATE TABLE {table} ({', '.join(header)})")
        con.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(header))})",
                        [[typed(v) if h not in ("po_number", "advertiser_id") else v for h, v in zip(header, r)] for r in body])


def q(con, sql):
    cur = con.execute(sql)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def main():
    OUT.mkdir(exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    load(con)
    for name in ("staging", "tests", "marts"):
        con.executescript((ROOT / "sql" / f"{name}.sql").read_text())
    con.commit()

    tests = q(con, "SELECT * FROM test_results ORDER BY test_id")
    blocking = [t for t in tests if t["severity"] == "error" and t["layer"] != "raw" and t["failures"] > 0]
    if blocking:
        raise SystemExit(f"Blocking test failures: {blocking}")

    quarters = {r["quarter"]: r for r in q(con, "SELECT * FROM mart_quarter")}
    weekly = q(con, "SELECT * FROM mart_weekly ORDER BY week_num")
    adoption = q(con, "SELECT * FROM mart_adoption_weekly ORDER BY week_num, product")
    last = [r for r in adoption if r["week_num"] == 26]
    auto_accounts = q(con, "SELECT * FROM mart_auto_accounts")
    funnel = {k: sum(r[k] for r in auto_accounts) for k in ("pitched", "tested", "adopted", "sustained")}
    funnel["eligible"] = len(auto_accounts)
    exceptions = q(con, "SELECT * FROM mart_po_exceptions ORDER BY CASE severity WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, amount_usd DESC")
    attain = q(con, "SELECT * FROM mart_attainment ORDER BY attainment")
    w17 = next(r for r in weekly if r["week_num"] == 17)

    results = {
        "as_of": "2026-10-04",
        "quarters": quarters,
        "weekly": weekly,
        "week17": {"raw": w17["raw_spend"], "clean": w17["spend"], "inflation": w17["raw_spend"] - w17["spend"],
                   "duplicate_rows": q(con, "SELECT (SELECT COUNT(*) FROM raw_ad_spend_export) - (SELECT COUNT(*) FROM stg_ad_spend) AS n")[0]["n"]},
        "product_quarter": q(con, "SELECT * FROM mart_product_quarter ORDER BY product, quarter"),
        "adoption_weekly": adoption,
        "adoption_last": last,
        "auto_funnel": funnel,
        "auto_by_csm": q(con, "SELECT * FROM mart_auto_by_csm"),
        "auto_by_vertical": q(con, "SELECT * FROM mart_auto_by_vertical"),
        "exceptions": exceptions,
        "exception_summary": q(con, "SELECT control, severity, COUNT(*) AS n, SUM(amount_usd) AS amount_usd FROM mart_po_exceptions GROUP BY control, severity ORDER BY CASE severity WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END"),
        "harbourline": q(con, "SELECT COUNT(*) AS n, SUM(amount_usd) AS over_usd FROM mart_po_exceptions WHERE control = 'Spend above PO' AND agency_name = 'Harbourline Media'")[0],
        "attainment": attain,
        "attainment_summary": q(con, "SELECT status, COUNT(*) AS n, SUM(spend) AS spend, SUM(committed_usd) AS committed FROM mart_attainment GROUP BY status"),
        "cpa_question": q(con, "SELECT * FROM mart_cpa_question"),
        "qbr": q(con, "SELECT * FROM mart_qbr ORDER BY quarter, spend DESC"),
        "tests": tests,
        "counts": q(con, """SELECT (SELECT COUNT(*) FROM stg_advertisers WHERE is_test = 0) AS client_accounts,
                                   (SELECT COUNT(*) FROM stg_advertisers WHERE is_test = 1) AS test_accounts,
                                   (SELECT COUNT(*) FROM raw_ad_spend_export) AS raw_rows,
                                   (SELECT COUNT(*) FROM fct_spend) AS fact_rows,
                                   (SELECT COUNT(*) FROM stg_purchase_orders) AS pos""")[0],
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=1, default=float))
    print(json.dumps({"tests": [(t["test_id"], t["layer"], t["severity"], t["failures"]) for t in tests]}))
    print("quarters", {k: (round(v["spend"]), round(v["roas"], 2), v["active_advertisers"]) for k, v in quarters.items()})
    print("week17", results["week17"])
    print("adoption wk26", [(r["product"], r["adopters_all"], r["active_all"], round(r["rate_naive"], 3), r["adopters_clean"], r["active_clean"], round(r["rate_clean"], 3)) for r in last])
    print("funnel", funnel)
    print("by csm", [(r["csm_name"], r["eligible"], r["pitched"], r["adopted"], round(r["pitch_rate"], 2), round(r["adoption_rate"], 2)) for r in results["auto_by_csm"]])
    print("by vertical", [(r["vertical"], r["pitched"], r["tested"], round(r["test_rate_when_pitched"] or 0, 2)) for r in results["auto_by_vertical"]])
    print("exceptions", [(r["control"], r["n"], round(r["amount_usd"] or 0)) for r in results["exception_summary"]])
    print("harbourline", results["harbourline"])
    print("attainment", results["attainment_summary"])
    print("cpa q", results["cpa_question"])
    print("counts", results["counts"])


if __name__ == "__main__":
    main()
