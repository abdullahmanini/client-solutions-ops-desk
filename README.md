# Client Solutions Ops Desk

A working model of the reporting behind a client solutions team at a short-video ad platform: weekly
spend and ad metrics, product adoption, a launch funnel, purchase-order controls, delivery against
commitments, a metric guide for sales and a quarterly business review. It comes as an Excel workbook
(with PivotTables) and as a one-page site laid out like a vertical video feed.

**Built by:** Abdullah Al Mneni, Business Technology Management, Toronto Metropolitan University
**Written for:** TikTok's Client Solutions Intern (GBS-NA) posting, Toronto, Summer 2027 (job A33712A)
**Built with:** Claude Code

> **Independent concept, synthetic data.** Not affiliated with or endorsed by TikTok, ByteDance or any
> ad platform. "Loopwave Ads", every advertiser, agency, CSM and number comes from the seeded model in
> `python/generate_data.py`. No real ad-platform data or product names are used.

## Why these pieces

The posting asks the intern to build and maintain internal dashboards, track product adoption, support
internal controls and reporting, track budgets and purchase orders, answer sales questions about
metrics, and prepare business-review material, using Excel or Google Sheets (pivot tables, formulas,
charts) and ideally a BI tool. Each piece below maps to one of those lines.

| Posting line | Where it is |
|---|---|
| Excel / Sheets: pivot tables, formulas, charts | `outputs/client_solutions_ops_desk.xlsx`: 2 PivotTables, SUMIFS / COUNTIFS / INDEX-MATCH on every reporting tab, 5 charts, conditional flags |
| Dashboards and reporting views on product adoption | Adoption tab and clip; Auto Funnel tab and clip |
| Internal controls, budgets and purchase orders | PO Controls tab and clip (`mart_po_exceptions`) |
| Answer sales questions on product and performance metrics | Metric Guide tab; "sales question" and metric clips |
| Reports for business reviews | QBR tab (rebuilds for any account) and clip |
| Accurate, organized data | 17 SQL data tests (`sql/tests.sql`) |

## Headline results (synthetic)

- **Q3 vs Q2:** spend $38.01M vs $34.42M (+10.4%), ROAS 2.51x vs 2.37x, CPA $21.57 vs $21.90,
  149 active client advertisers in Q3.
- **Planted problem 1, duplicate export:** the week-17 US file was loaded twice (158 rows). The raw
  export shows $3.75M for the week of Jul 27; the real figure is $2.56M ($1.19M overstated). Test T01
  catches it; staging keeps the latest load per key; T02 confirms the staged table is unique.
- **Planted problem 2, test accounts:** 8 internal QA sandbox accounts run the new Auto-Campaigns
  product every week. Counted as clients, adoption reads 32.7% (49 of 150); clients only it is 28.9%
  (41 of 142). One in six "adopters" was internal.
- **Launch funnel (Auto-Campaigns, launched Jun 8):** 149 eligible, 103 pitched, 54 tested, 41 adopted,
  27 sustained. One CSM's book was pitched 36% of the time against 77% for the rest of the team;
  matching the team rate would add about 5 adopters (at the team's 40% pitched-to-adopted rate).
- **Planted problem 3, purchase orders:** Harbourline Media's Q3 POs were copied from Q2 while its
  accounts grew. 6 accounts went over, $588k in total. Four other accounts booked July spend on their
  expired Q2 POs, which also pushed those POs over. 9 invoice-billed accounts have $547k of spend with no
  PO number, one PO number was issued to two advertisers, and 34 accounts are spending with no Q4 PO.
- **Q3 attainment:** the book delivered 101% of commitment, which hides 36 accounts under 90%
  ($1.75M short of their commitments). 82 on plan, 34 over 110%.
- **A sales question:** "Is Auto-Campaigns cheaper per conversion?" The dashboard total says 40%
  cheaper ($14.56 vs $24.32 CPA). Its adopters lean to Gaming and Retail (54% of its spend vs 38% for
  In-Feed Video), where conversions are cheap anyway. In the same accounts and weeks the gap is 26%
  ($14.56 vs $19.64). The model's true effect is 27%.
- **QBR (Maple & Main Grocers, fictional):** Q3 spend $397k (+3.1%), ROAS 4.03x; Auto-Campaigns test
  returned 4.99x vs 3.85x for In-Feed Video. Recommendations: scale the test in steps, trial Shoppable
  Video before the holidays (9 of 26 retail peers run it, at 5.84x vs 3.82x ROAS), sign the Q4 PO.

## Repository

| Path | What it is |
|---|---|
| `python/generate_data.py` | Seeded model (seed 20271): 160 accounts, 6 products, 26 weeks, POs, CSM activity, commitments, with the four planted problems |
| `python/pipeline.py` | Loads the CSVs into SQLite, runs staging, tests and marts, stops on a blocking test failure, writes `outputs/results.json` |
| `sql/staging.sql` | De-duplication, typing, test-account flag, client-only reporting fact |
| `sql/tests.sql` | 17 data tests with layer and severity (error / warn) |
| `sql/marts.sql` | Weekly, quarter, product, adoption, funnel, PO exceptions, attainment, CPA question, QBR |
| `python/build_workbook.py` | The Excel workbook (openpyxl), plus the PivotTable XML openpyxl cannot write |
| `python/build_site.py`, `site/template.html` | The one-page site (`index.html`) |
| `data/raw/` | The generated raw exports (CSV) |
| `outputs/` | `client_solutions_ops_desk.xlsx`, `results.json`, `model_truth.json` |
| `docs/` | Metric guide, QBR summary, and how the planted problems were found |

## Run it

```bash
python3 python/generate_data.py
python3 python/pipeline.py
python3 python/build_workbook.py
python3 python/build_site.py
```

Python 3.9+, standard library plus `openpyxl`. Open the workbook in Excel or Google Sheets; both
recalculate the formulas on open, and Excel rebuilds the two PivotTables from the Spend Data tab
(right-click a pivot and choose Refresh after editing data). The workbook's formulas were checked in
Excel 16 against the SQL results.

## Limits

- Synthetic data. The planted problems are known in advance, so finding them shows the method, not
  investigative luck. `outputs/model_truth.json` lists them.
- "Adopted" uses a $500 / 4-week threshold. A real team would agree the definition with product.
- The extra-adopters estimate assumes the low-coverage book converts pitches at the team rate.
- No Looker or Tableau work. The site and the workbook cover the dashboard; a Looker Studio version
  would read the same CSVs.
