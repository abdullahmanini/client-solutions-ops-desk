# How the planted problems were found

The model plants four problems (listed in `outputs/model_truth.json`). This is the order a reviewer
would hit them and the check that surfaces each.

| Problem | First signal | Check | Fix |
|---|---|---|---|
| Week-17 US export loaded twice (158 rows, $1.19M) | Weekly spend +46% in one week, then back | T01 (raw key not unique), T16 (raw week-over-week move above 25%) | Staging keeps the latest load per week, advertiser and product; T02 and T17 pass |
| 8 QA sandbox accounts counted as Auto-Campaigns adopters | Adoption of a 4-month-old product at 32.7% | T10 (sandbox names flagged), T11 (reporting excludes tests) | Reporting fact is clients only: 28.9% |
| Harbourline Media Q3 POs copied from Q2 | 6 accounts at 124-141% of PO | T15 (spend within PO amount) | Exceptions queue, High; ask the agency for PO amendments |
| Billing hygiene: Q2 POs used in July, missing PO numbers, one PO number on two advertisers | Flags in the PO Controls tab | T12, T13, T14 | Exceptions queue; finance to re-issue the duplicate number |

Two further findings came out of the reporting rather than the plants: the launch funnel's pitch gap
(one book pitched 36% vs 77%), and the CPA mix effect behind the "40% cheaper" claim.
