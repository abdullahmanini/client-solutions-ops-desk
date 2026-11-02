"""Build the one-page site from outputs/results.json.

Writes index.html (full document, for GitHub Pages) and outputs/artifact.html (the same page without
the document skeleton, for a claude.ai artifact). The page template is site/template.html.

Run: python3 python/build_site.py   (after pipeline.py)
"""
import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
R = json.loads((ROOT / "outputs" / "results.json").read_text())


def r2(x, n=2):
    return None if x is None else round(x, n)


def main():
    q2, q3 = R["quarters"]["2026-Q2"], R["quarters"]["2026-Q3"]
    kpi = {k: {"q2": r2(q2[k], 4), "q3": r2(q3[k], 4)} for k in ("spend", "impressions", "clicks", "conversions", "conversion_value", "cpm", "ctr", "cvr", "cpa", "roas", "active_advertisers")}
    weekly = [{"w": r["week_num"], "d": r["week_start"], "raw": round(r["raw_spend"]), "clean": round(r["spend"])} for r in R["weekly"]]
    adoption = [{"p": r["product"], "naive": r2(r["rate_naive"], 4), "clean": r2(r["rate_clean"], 4),
                 "an": r["adopters_all"], "dn": r["active_all"], "ac": r["adopters_clean"], "dc": r["active_clean"]}
                for r in R["adoption_last"]]
    adoption.sort(key=lambda r: -r["clean"])
    auto_trend = [{"w": r["week_num"], "naive": r2(r["rate_naive"], 4), "clean": r2(r["rate_clean"], 4)}
                  for r in R["adoption_weekly"] if r["product"] == "Auto-Campaigns"]
    csm = [{"n": r["csm_name"], "e": r["eligible"], "p": r["pitched"], "a": r["adopted"], "pr": r2(r["pitch_rate"], 4), "ar": r2(r["adoption_rate"], 4)} for r in R["auto_by_csm"]]
    low = min(csm, key=lambda r: r["pr"])
    rest_p = sum(r["p"] for r in csm if r is not low)
    rest_e = sum(r["e"] for r in csm if r is not low)
    f = R["auto_funnel"]
    lift = low["e"] * (rest_p / rest_e - low["pr"]) * (f["adopted"] / f["pitched"])
    exceptions = [{"c": e["control"], "s": e["severity"], "adv": e["advertiser_name"], "ag": e["agency_name"], "po": e["po_number"],
                   "amt": round(e["amount_usd"] or 0), "d": e["detail"]} for e in R["exceptions"]]
    att = [{"n": a["advertiser_name"], "v": a["vertical"], "c": round(a["committed_usd"]), "s": round(a["spend"]), "a": r2(a["attainment"], 4), "st": a["status"]} for a in R["attainment"]]
    data = {
        "asOf": R["as_of"], "kpi": kpi, "weekly": weekly, "week17": {k: round(v) for k, v in R["week17"].items()},
        "adoption": adoption, "autoTrend": auto_trend,
        "funnel": f, "csm": csm, "lowCsm": {"name": low["n"], "rate": low["pr"], "teamRate": round(rest_p / rest_e, 4), "extraAdopters": round(lift, 1)},
        "vertical": [{"v": r["vertical"], "p": r["pitched"], "t": r["tested"], "r": r2(r["test_rate_when_pitched"], 4)} for r in R["auto_by_vertical"]],
        "exceptions": exceptions,
        "excSummary": [{"c": r["control"], "s": r["severity"], "n": r["n"], "amt": round(r["amount_usd"] or 0)} for r in R["exception_summary"]],
        "harbourline": {"n": R["harbourline"]["n"], "amt": round(R["harbourline"]["over_usd"])},
        "attainment": att,
        "attSummary": {r["status"]: {"n": r["n"], "spend": round(r["spend"]), "committed": round(r["committed"])} for r in R["attainment_summary"]},
        "cpa": [{"k": r["comparison"], "auto": r2(r["auto_cpa"]), "feed": r2(r["infeed_cpa"]),
                 "gr_auto": r2(r["auto_share_gaming_retail"], 4), "gr_feed": r2(r["infeed_share_gaming_retail"], 4)} for r in R["cpa_question"]],
        "qbr": [{"q": r["quarter"], "p": r["product"], "s": round(r["spend"]), "c": r["conversions"], "v": round(r["conversion_value"])} for r in R["qbr"]],
        "tests": [{"id": t["test_id"], "l": t["layer"], "d": t["description"], "sev": t["severity"], "f": t["failures"]} for t in R["tests"]],
        "counts": R["counts"],
    }
    blob = json.dumps(data, separators=(",", ":"))
    page = (ROOT / "site" / "template.html").read_text().replace("/*__DATA__*/null", blob)
    (ROOT / "outputs" / "artifact.html").write_text(page)
    full = ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\">\n"
            "<style>html,body{margin:0}[hidden]{display:none!important}:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}</style>\n"
            "</head>\n<body>\n" + page + "\n</body>\n</html>\n")
    (ROOT / "index.html").write_text(full)
    print(f"site data {len(blob) / 1024:.0f} KB; lowest pitch rate {low['n']} {low['pr']:.0%} vs {rest_p / rest_e:.0%}, ~{lift:.1f} extra adopters")


if __name__ == "__main__":
    main()
