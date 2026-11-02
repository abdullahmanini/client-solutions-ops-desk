"""Seeded synthetic data for the Client Solutions Ops Desk.

A fictional short-video ad platform ("Loopwave Ads") and its North America Client Solutions team,
26 weeks from Apr 6 to Oct 4, 2026 (Q2 = weeks 1-13, Q3 = weeks 14-26).

Everything here is made up. Four problems are planted on purpose so the reporting has to catch them:
  1. The week-17 export for US accounts was loaded twice (duplicate rows).
  2. Harbourline Media's Q3 purchase orders were copied from Q2 while spend grew, so six accounts
     spend past their PO.
  3. Eight internal QA sandbox accounts run Auto-Campaigns every week and look like adopters.
  4. Billing hygiene: Q2 POs still used on July spend, PO numbers missing on invoice-billed rows,
     and one PO number issued to two advertisers.

Run: python3 python/generate_data.py   (writes data/raw/*.csv and outputs/model_truth.json)
"""
import csv
import json
import math
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 20271
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
WEEKS = 26
START = date(2026, 4, 6)
AS_OF = date(2026, 10, 4)


def week_start(w):
    return START + timedelta(days=7 * (w - 1))


def quarter(w):
    return "2026-Q2" if w <= 13 else "2026-Q3"


# vertical: share of accounts, CPM ($), CTR, CVR (conversions per click), value per conversion ($)
VERTICALS = {
    "Retail":             (0.22, 6.4, 0.0110, 0.032, 68),
    "CPG":                (0.15, 5.2, 0.0080, 0.015, 22),
    "Gaming":             (0.12, 7.8, 0.0140, 0.045, 18),
    "Financial Services": (0.11, 9.5, 0.0070, 0.020, 140),
    "Entertainment":      (0.12, 6.0, 0.0120, 0.028, 25),
    "Travel":             (0.10, 7.2, 0.0090, 0.018, 310),
    "Auto":               (0.08, 8.4, 0.0060, 0.012, 240),
    "Telecom":            (0.10, 8.0, 0.0080, 0.016, 120),
}

# product: efficiency multipliers on CPM, CTR, CVR
PRODUCTS = {
    "In-Feed Video":       (1.00, 1.00, 1.00),
    "Boosted Posts":       (0.85, 1.15, 0.95),
    "Search Placements":   (1.60, 2.40, 1.30),
    "Shoppable Video":     (1.10, 1.25, 1.35),
    "Auto-Campaigns":      (0.95, 1.10, 1.18),
    "Lift Studies":        (1.00, 0.90, 0.90),
}
AUTO_LAUNCH_WEEK = 10

AGENCIES = [
    ("AG01", "Harbourline Media"), ("AG02", "Northgate Collective"), ("AG03", "Brightwater Group"),
    ("AG04", "Cedar & Stone"), ("AG05", "Parallel Agency"), ("AG06", "Kitestring Media"),
    ("AG07", "Tidewell Partners"),
]
CSMS = [
    ("CSM1", "Priya Natarajan"), ("CSM2", "Marcus Bell"), ("CSM3", "Elena Sokolova"),
    ("CSM4", "Daniel Osei"), ("CSM5", "Hana Kim"), ("CSM6", "Luis Ortega"),
]
# how often each CSM pitches Auto-Campaigns (CSM2 is stretched across the largest book)
CSM_PITCH = {"CSM1": 0.80, "CSM2": 0.38, "CSM3": 0.72, "CSM4": 0.66, "CSM5": 0.78, "CSM6": 0.62}

NAME_A = ["North", "Maple", "Harbor", "Silver", "Prairie", "Lake", "Summit", "Cedar", "Iron", "Blue",
          "Golden", "Copper", "Pine", "Granite", "River", "Aurora", "Coastal", "Union", "Bright",
          "True", "Red", "Oak", "Echo", "Polar", "Metro", "Swift", "Willow", "Juniper", "Atlas", "Lumen"]
NAME_B = {
    "Retail": ["Outfitters", "Home", "Goods", "Market", "Apparel", "Supply"],
    "CPG": ["Foods", "Beverage Co.", "Snacks", "Naturals", "Brands", "Pantry"],
    "Gaming": ["Games", "Studios", "Interactive", "Play", "Arcade", "Labs"],
    "Financial Services": ["Bank", "Credit Union", "Wealth", "Pay", "Insurance", "Lending"],
    "Entertainment": ["Pictures", "Streaming", "Live", "Music", "Records", "Media"],
    "Travel": ["Air", "Hotels", "Getaways", "Rail", "Cruises", "Trips"],
    "Auto": ["Motors", "Auto Group", "Tires", "EV", "Dealers", "Mobility"],
    "Telecom": ["Mobile", "Wireless", "Connect", "Fibre", "Telecom", "Networks"],
}


def season(w):
    """Spend seasonality: soft July, back-to-school lift in August, steady September."""
    d = week_start(w)
    if d.month == 7:
        return 0.92
    if d.month == 8:
        return 1.10
    if d.month == 9:
        return 1.04
    return 1.0


def main():
    rng = random.Random(SEED)
    RAW.mkdir(parents=True, exist_ok=True)
    (ROOT / "outputs").mkdir(exist_ok=True)

    # ---------- advertisers ----------
    advertisers = []
    used = set()
    vnames = list(VERTICALS)
    vweights = [VERTICALS[v][0] for v in vnames]
    n_real = 152
    for i in range(1, n_real + 1):
        v = rng.choices(vnames, vweights)[0]
        while True:
            name = f"{rng.choice(NAME_A)} {rng.choice(NAME_B[v])}"
            if name not in used:
                used.add(name)
                break
        tier = "Enterprise" if rng.random() < 0.30 else "Mid-Market"
        market = "US" if rng.random() < 0.58 else "CA"
        agency = "DIRECT" if rng.random() < 0.34 else rng.choice(AGENCIES)[0]
        billing = "card" if (agency == "DIRECT" and tier == "Mid-Market" and rng.random() < 0.45) else "invoice"
        base = rng.lognormvariate(math.log(42000 if tier == "Enterprise" else 7000), 0.45)
        advertisers.append({
            "advertiser_id": f"ADV{i:03d}", "advertiser_name": name, "vertical": v, "tier": tier,
            "market": market, "agency_id": agency, "csm_id": rng.choice(CSMS)[0],
            "billing_type": billing, "account_type": "client", "_base": base,
        })
    # Harbourline needs enough accounts for the planted overspend
    hb = [a for a in advertisers if a["agency_id"] == "AG01"]
    for a in advertisers:
        if len(hb) >= 9:
            break
        if a["agency_id"] not in ("AG01", "DIRECT") and a not in hb:
            a["agency_id"] = "AG01"
            hb.append(a)
    # a showcase enterprise retail account for the QBR
    qbr = next(a for a in advertisers if a["tier"] == "Enterprise" and a["vertical"] == "Retail")
    qbr["advertiser_name"] = "Maple & Main Grocers"
    qbr["market"] = "CA"
    for k in range(1, 9):
        advertisers.append({
            "advertiser_id": f"ADV{n_real + k:03d}", "advertiser_name": f"QA Sandbox {k:02d}",
            "vertical": rng.choice(vnames), "tier": "Mid-Market", "market": rng.choice(["US", "CA"]),
            "agency_id": "DIRECT", "csm_id": rng.choice(CSMS)[0], "billing_type": "card",
            "account_type": "internal_test", "_base": 300.0,
        })

    # ---------- product mix and the Auto-Campaigns funnel ----------
    truth = {"pauses": []}
    for a in advertisers:
        a["_products"] = {"In-Feed Video": 1.0}
        if a["account_type"] == "internal_test":
            a["_auto_start"] = AUTO_LAUNCH_WEEK
            a["_products"] = {"In-Feed Video": 0.3}
            continue
        if rng.random() < 0.55:
            a["_products"]["Boosted Posts"] = rng.uniform(0.15, 0.30)
        if rng.random() < 0.30:
            a["_products"]["Search Placements"] = rng.uniform(0.08, 0.18)
        if rng.random() < (0.45 if a["vertical"] in ("Retail", "CPG") else 0.08):
            a["_products"]["Shoppable Video"] = rng.uniform(0.15, 0.30)
        if a["tier"] == "Enterprise" and rng.random() < 0.35:
            a["_products"]["Lift Studies"] = rng.uniform(0.04, 0.08)
        # pause: some mid-market accounts go dark for the rest of the period
        a["_pause"] = rng.randint(6, 24) if (a["tier"] == "Mid-Market" and rng.random() < 0.08) else None
        if a["_pause"]:
            truth["pauses"].append(a["advertiser_id"])
        # Auto-Campaigns funnel: pitched -> tested -> adopted (kept spending)
        p_pitch = CSM_PITCH[a["csm_id"]] * (1.1 if a["tier"] == "Enterprise" else 0.95)
        a["_pitch_week"] = rng.randint(AUTO_LAUNCH_WEEK, 23) if rng.random() < p_pitch else None
        a["_auto_start"] = None
        a["_auto_stop"] = None
        if a["_pitch_week"]:
            p_test = {"Gaming": 0.72, "Retail": 0.66, "Entertainment": 0.60, "Financial Services": 0.34,
                      "Auto": 0.40}.get(a["vertical"], 0.52)
            if rng.random() < p_test:
                a["_auto_start"] = a["_pitch_week"] + rng.randint(1, 3)
                if rng.random() > 0.70:  # tested, then stopped after a few weeks
                    a["_auto_stop"] = a["_auto_start"] + rng.randint(1, 3)
                a["_products"]["Auto-Campaigns"] = rng.uniform(0.15, 0.28)

    # ---------- weekly spend ----------
    def metrics(a, product, spend):
        cpm0, ctr0, cvr0 = VERTICALS[a["vertical"]][1:4]
        val = VERTICALS[a["vertical"]][4]
        m_cpm, m_ctr, m_cvr = PRODUCTS[product]
        impressions = int(spend / (cpm0 * m_cpm * rng.uniform(0.85, 1.15)) * 1000)
        clicks = int(impressions * ctr0 * m_ctr * rng.uniform(0.8, 1.2))
        conversions = int(clicks * cvr0 * m_cvr * rng.uniform(0.75, 1.25))
        value = round(conversions * val * rng.uniform(0.85, 1.15), 2)
        return impressions, clicks, conversions, value

    spend_rows = []
    for a in advertisers:
        growth = rng.uniform(-0.002, 0.012)  # weekly drift
        if a["agency_id"] == "AG01" and a["account_type"] == "client":
            growth = 0.028  # Harbourline accounts scale fast in Q3
        for w in range(1, WEEKS + 1):
            if a.get("_pause") and w >= a["_pause"]:
                continue
            budget = a["_base"] * season(w) * (1 + growth) ** (w - 1) * rng.uniform(0.85, 1.15)
            mix = dict(a["_products"])
            auto_on = a["_auto_start"] and w >= a["_auto_start"] and not (a.get("_auto_stop") and w > a["_auto_stop"])
            if a["account_type"] == "internal_test":
                mix["Auto-Campaigns"] = 0.7 if w >= AUTO_LAUNCH_WEEK else 0
            elif not auto_on:
                mix.pop("Auto-Campaigns", None)
            mix = {p: s for p, s in mix.items() if s > 0}
            others = sum(s for p, s in mix.items() if p != "In-Feed Video")
            mix["In-Feed Video"] = max(0.2, 1 - others) if a["account_type"] == "client" else mix["In-Feed Video"]
            total = sum(mix.values())
            for p, s in mix.items():
                spend = round(budget * s / total, 2)
                if spend < 25:
                    continue
                imp, clk, conv, val = metrics(a, p, spend)
                spend_rows.append({
                    "load_id": 1000 + w, "week_start": week_start(w).isoformat(),
                    "advertiser_id": a["advertiser_id"], "product": p, "spend_usd": spend,
                    "impressions": imp, "clicks": clk, "conversions": conv,
                    "conversion_value_usd": val, "po_number": "",
                })

    # ---------- purchase orders ----------
    adv_by_id = {a["advertiser_id"]: a for a in advertisers}
    q_spend = {}
    for r in spend_rows:
        w = (date.fromisoformat(r["week_start"]) - START).days // 7 + 1
        key = (r["advertiser_id"], quarter(w))
        q_spend[key] = q_spend.get(key, 0) + r["spend_usd"]

    pos = []
    po_lookup = {}
    seq = 4100
    hb_over = []
    for a in advertisers:
        if a["billing_type"] != "invoice":
            continue
        for q, (s, e) in {"2026-Q2": (date(2026, 4, 1), date(2026, 6, 30)),
                          "2026-Q3": (date(2026, 7, 1), date(2026, 9, 30)),
                          "2026-Q4": (date(2026, 10, 1), date(2026, 12, 31))}.items():
            seq += 1
            if q == "2026-Q4":
                # Q4 POs exist only for some accounts yet; the rest are a renewal gap to chase
                if rng.random() < 0.62:
                    amt = q_spend.get((a["advertiser_id"], "2026-Q3"), 0) * rng.uniform(1.0, 1.2)
                else:
                    continue
            else:
                amt = q_spend.get((a["advertiser_id"], q), 0) * rng.uniform(1.03, 1.18)
            if a["agency_id"] == "AG01" and q == "2026-Q3" and len(hb_over) < 6:
                # PLANT 2: Q3 PO copied from the Q2 amount
                amt = pos[-1]["po_amount_usd"]
                hb_over.append(a["advertiser_id"])
            po = {"po_number": f"PO-{seq}", "advertiser_id": a["advertiser_id"],
                  "agency_id": a["agency_id"], "quarter": q, "po_start": s.isoformat(),
                  "po_end": e.isoformat(), "po_amount_usd": round(amt, -2), "currency": "USD"}
            if amt <= 0:
                continue
            pos.append(po)
            po_lookup[(a["advertiser_id"], q)] = po["po_number"]

    # PLANT 4c: one PO number issued twice
    dup_src = next(p for p in pos if p["quarter"] == "2026-Q3" and adv_by_id[p["advertiser_id"]]["agency_id"] == "AG04")
    dup_tgt = next(p for p in pos if p["quarter"] == "2026-Q3" and adv_by_id[p["advertiser_id"]]["agency_id"] == "AG04"
                   and p["advertiser_id"] != dup_src["advertiser_id"])
    truth["duplicate_po"] = {"po_number": dup_src["po_number"],
                             "advertisers": [dup_src["advertiser_id"], dup_tgt["advertiser_id"]],
                             "replaced": dup_tgt["po_number"]}
    dup_tgt["po_number"] = dup_src["po_number"]
    po_lookup[(dup_tgt["advertiser_id"], "2026-Q3")] = dup_src["po_number"]

    # stamp PO numbers on spend rows
    invoice_ids = [a["advertiser_id"] for a in advertisers if a["billing_type"] == "invoice"]
    stale = rng.sample([i for i in invoice_ids if adv_by_id[i]["agency_id"] != "AG01"], 4)
    missing = rng.sample([i for i in invoice_ids if i not in stale and adv_by_id[i]["agency_id"] != "AG01"], 9)
    for r in spend_rows:
        a = adv_by_id[r["advertiser_id"]]
        if a["billing_type"] != "invoice":
            continue
        w = (date.fromisoformat(r["week_start"]) - START).days // 7 + 1
        q = quarter(w)
        r["po_number"] = po_lookup.get((r["advertiser_id"], q), "")
        if r["advertiser_id"] in stale and 14 <= w <= 16:
            r["po_number"] = po_lookup[(r["advertiser_id"], "2026-Q2")]  # PLANT 4a: expired PO
        if r["advertiser_id"] in missing and 20 <= w <= 23:
            r["po_number"] = ""  # PLANT 4b: missing PO number
    truth["stale_po_accounts"] = sorted(stale)
    truth["missing_po_accounts"] = sorted(missing)
    truth["harbourline_overspend_accounts"] = sorted(hb_over)

    # PLANT 1: week-17 US export loaded twice
    w17 = week_start(17).isoformat()
    dupes = []
    for r in spend_rows:
        if r["week_start"] == w17 and adv_by_id[r["advertiser_id"]]["market"] == "US":
            d = dict(r)
            d["load_id"] = 2017
            dupes.append(d)
    spend_rows.extend(dupes)
    truth["week17_duplicate_rows"] = len(dupes)
    truth["week17_duplicate_spend"] = round(sum(d["spend_usd"] for d in dupes), 2)

    # ---------- CSM activity log (pitches) ----------
    pitches = []
    for a in advertisers:
        if a["account_type"] == "client" and a.get("_pitch_week"):
            pitches.append({"activity_id": f"ACT{len(pitches) + 1:04d}", "advertiser_id": a["advertiser_id"],
                            "csm_id": a["csm_id"], "product": "Auto-Campaigns",
                            "activity_type": "pitch", "activity_date": (week_start(a["_pitch_week"]) + timedelta(days=rng.randint(0, 4))).isoformat()})

    # ---------- quarterly commitments (sales plan) ----------
    commitments = []
    for a in advertisers:
        if a["account_type"] != "client":
            continue
        for q in ("2026-Q2", "2026-Q3"):
            actual = q_spend.get((a["advertiser_id"], q), 0)
            if actual == 0 and q == "2026-Q2":
                continue
            plan_base = q_spend.get((a["advertiser_id"], "2026-Q2"), actual)
            committed = plan_base * rng.uniform(0.92, 1.18) * (1.04 if q == "2026-Q3" else 1.0)
            commitments.append({"advertiser_id": a["advertiser_id"], "quarter": q,
                                "committed_usd": round(committed, -2)})

    # ---------- write ----------
    def write(name, rows, fields):
        with open(RAW / name, "w", newline="") as f:
            wr = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            wr.writeheader()
            wr.writerows(rows)

    write("advertisers.csv", advertisers, ["advertiser_id", "advertiser_name", "vertical", "tier", "market",
                                            "agency_id", "csm_id", "billing_type", "account_type"])
    write("agencies.csv", [{"agency_id": i, "agency_name": n} for i, n in AGENCIES] +
          [{"agency_id": "DIRECT", "agency_name": "Direct (no agency)"}], ["agency_id", "agency_name"])
    write("csms.csv", [{"csm_id": i, "csm_name": n} for i, n in CSMS], ["csm_id", "csm_name"])
    write("products.csv", [{"product": p, "launch_week_start": (week_start(AUTO_LAUNCH_WEEK).isoformat() if p == "Auto-Campaigns" else "2026-01-01")} for p in PRODUCTS],
          ["product", "launch_week_start"])
    rng.shuffle(spend_rows)
    spend_rows.sort(key=lambda r: (r["load_id"], r["week_start"]))
    write("ad_spend_export.csv", spend_rows, ["load_id", "week_start", "advertiser_id", "product", "spend_usd",
                                               "impressions", "clicks", "conversions", "conversion_value_usd", "po_number"])
    write("purchase_orders.csv", pos, ["po_number", "advertiser_id", "agency_id", "quarter", "po_start", "po_end",
                                        "po_amount_usd", "currency"])
    write("csm_activity.csv", pitches, ["activity_id", "advertiser_id", "csm_id", "product", "activity_type", "activity_date"])
    write("quarterly_commitments.csv", commitments, ["advertiser_id", "quarter", "committed_usd"])

    truth["test_accounts"] = [a["advertiser_id"] for a in advertisers if a["account_type"] == "internal_test"]
    truth["qbr_account"] = qbr["advertiser_id"]
    truth["seed"] = SEED
    (ROOT / "outputs" / "model_truth.json").write_text(json.dumps(truth, indent=2))
    print(f"advertisers {len(advertisers)}, spend rows {len(spend_rows)} (incl. {len(dupes)} duplicates), "
          f"POs {len(pos)}, pitches {len(pitches)}, commitments {len(commitments)}")


if __name__ == "__main__":
    main()
