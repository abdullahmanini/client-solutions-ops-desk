-- Marts: the reporting views behind each card on the page and each tab in the workbook.
-- "Last 4 weeks" means weeks 23-26 (Sep 7 - Oct 4, 2026). Adoption = at least $500 on a product in 4 weeks.

-- Weekly spend: what the raw export says vs the de-duplicated reporting fact.
DROP TABLE IF EXISTS mart_weekly;
CREATE TABLE mart_weekly AS
WITH raw_w AS (
  SELECT r.week_start, SUM(r.spend_usd) AS raw_spend
  FROM raw_ad_spend_export r JOIN stg_advertisers a USING (advertiser_id)
  WHERE a.is_test = 0 GROUP BY r.week_start
)
SELECT f.week_num, f.week_start, f.quarter, r.raw_spend,
       SUM(f.spend_usd) AS spend, SUM(f.impressions) AS impressions, SUM(f.clicks) AS clicks,
       SUM(f.conversions) AS conversions, SUM(f.conversion_value_usd) AS conversion_value,
       COUNT(DISTINCT f.advertiser_id) AS active_advertisers
FROM fct_spend f JOIN raw_w r USING (week_start)
GROUP BY f.week_num, f.week_start, f.quarter, r.raw_spend
ORDER BY f.week_num;

-- Quarter summary with the standard ad metrics.
DROP TABLE IF EXISTS mart_quarter;
CREATE TABLE mart_quarter AS
SELECT quarter, SUM(spend_usd) AS spend, SUM(impressions) AS impressions, SUM(clicks) AS clicks,
       SUM(conversions) AS conversions, SUM(conversion_value_usd) AS conversion_value,
       COUNT(DISTINCT advertiser_id) AS active_advertisers,
       1000.0 * SUM(spend_usd) / SUM(impressions) AS cpm,
       1.0 * SUM(clicks) / SUM(impressions) AS ctr,
       1.0 * SUM(conversions) / SUM(clicks) AS cvr,
       SUM(spend_usd) / SUM(conversions) AS cpa,
       SUM(conversion_value_usd) / SUM(spend_usd) AS roas
FROM fct_spend GROUP BY quarter;

-- Product mix by quarter.
DROP TABLE IF EXISTS mart_product_quarter;
CREATE TABLE mart_product_quarter AS
SELECT product, quarter, SUM(spend_usd) AS spend, COUNT(DISTINCT advertiser_id) AS advertisers,
       SUM(spend_usd) / SUM(conversions) AS cpa, SUM(conversion_value_usd) / SUM(spend_usd) AS roas
FROM fct_spend GROUP BY product, quarter;

-- Rolling 4-week adoption by product, with and without the internal QA sandboxes.
DROP TABLE IF EXISTS mart_adoption_weekly;
CREATE TABLE mart_adoption_weekly AS
WITH weeks AS (SELECT DISTINCT week_num FROM stg_ad_spend WHERE week_num >= 4),
win AS (
  SELECT w.week_num, s.advertiser_id, s.product, SUM(s.spend_usd) AS spend4
  FROM weeks w JOIN stg_ad_spend s ON s.week_num BETWEEN w.week_num - 3 AND w.week_num
  GROUP BY w.week_num, s.advertiser_id, s.product
),
active AS (
  SELECT win.week_num,
         COUNT(DISTINCT win.advertiser_id) AS active_all,
         COUNT(DISTINCT CASE WHEN a.is_test = 0 THEN win.advertiser_id END) AS active_clean
  FROM win JOIN stg_advertisers a USING (advertiser_id) GROUP BY win.week_num
),
adopt AS (
  SELECT win.week_num, win.product,
         COUNT(DISTINCT CASE WHEN win.spend4 >= 500 THEN win.advertiser_id END) AS adopters_all,
         COUNT(DISTINCT CASE WHEN win.spend4 >= 500 AND a.is_test = 0 THEN win.advertiser_id END) AS adopters_clean
  FROM win JOIN stg_advertisers a USING (advertiser_id) GROUP BY win.week_num, win.product
)
SELECT adopt.week_num, adopt.product, active.active_all, active.active_clean,
       adopt.adopters_all, adopt.adopters_clean,
       1.0 * adopt.adopters_all / active.active_all AS rate_naive,
       1.0 * adopt.adopters_clean / active.active_clean AS rate_clean
FROM adopt JOIN active USING (week_num)
ORDER BY adopt.week_num, adopt.product;

-- Auto-Campaigns funnel per client account (eligible = spent in Q3).
DROP TABLE IF EXISTS mart_auto_accounts;
CREATE TABLE mart_auto_accounts AS
WITH eligible AS (SELECT DISTINCT advertiser_id FROM fct_spend WHERE quarter = '2026-Q3'),
auto AS (
  SELECT advertiser_id,
         SUM(spend_usd) AS auto_spend_total,
         SUM(CASE WHEN week_num >= 23 THEN spend_usd ELSE 0 END) AS auto_spend_last4,
         COUNT(DISTINCT CASE WHEN week_num >= 23 THEN week_num END) AS weeks_last4
  FROM fct_spend WHERE product = 'Auto-Campaigns' GROUP BY advertiser_id
)
SELECT a.advertiser_id, a.advertiser_name, a.vertical, a.tier, a.csm_id, a.csm_name,
       CASE WHEN p.advertiser_id IS NOT NULL THEN 1 ELSE 0 END AS pitched,
       CASE WHEN au.advertiser_id IS NOT NULL THEN 1 ELSE 0 END AS tested,
       CASE WHEN COALESCE(au.auto_spend_last4, 0) >= 500 THEN 1 ELSE 0 END AS adopted,
       CASE WHEN COALESCE(au.weeks_last4, 0) = 4 THEN 1 ELSE 0 END AS sustained,
       COALESCE(au.auto_spend_total, 0) AS auto_spend_total
FROM eligible e
JOIN stg_advertisers a USING (advertiser_id)
LEFT JOIN (SELECT DISTINCT advertiser_id FROM raw_csm_activity WHERE product = 'Auto-Campaigns') p USING (advertiser_id)
LEFT JOIN auto au USING (advertiser_id);

DROP TABLE IF EXISTS mart_auto_by_csm;
CREATE TABLE mart_auto_by_csm AS
SELECT csm_name, COUNT(*) AS eligible, SUM(pitched) AS pitched, SUM(tested) AS tested,
       SUM(adopted) AS adopted, SUM(sustained) AS sustained,
       1.0 * SUM(pitched) / COUNT(*) AS pitch_rate,
       1.0 * SUM(adopted) / COUNT(*) AS adoption_rate,
       1.0 * SUM(CASE WHEN pitched = 1 AND tested = 1 THEN 1 ELSE 0 END) / NULLIF(SUM(pitched), 0) AS test_rate_when_pitched
FROM mart_auto_accounts GROUP BY csm_name ORDER BY adoption_rate DESC;

DROP TABLE IF EXISTS mart_auto_by_vertical;
CREATE TABLE mart_auto_by_vertical AS
SELECT vertical, COUNT(*) AS eligible, SUM(pitched) AS pitched, SUM(tested) AS tested, SUM(adopted) AS adopted,
       1.0 * SUM(CASE WHEN pitched = 1 AND tested = 1 THEN 1 ELSE 0 END) / NULLIF(SUM(pitched), 0) AS test_rate_when_pitched
FROM mart_auto_accounts GROUP BY vertical ORDER BY test_rate_when_pitched DESC;

-- PO and billing controls: one row per exception.
DROP TABLE IF EXISTS mart_po_exceptions;
CREATE TABLE mart_po_exceptions AS
WITH booked AS (
  SELECT f.po_number, f.advertiser_id, SUM(f.spend_usd) AS spent
  FROM fct_spend f WHERE f.po_number IS NOT NULL GROUP BY f.po_number, f.advertiser_id
)
SELECT 'Spend above PO' AS control, 'High' AS severity, a.advertiser_id, a.advertiser_name, a.agency_name,
       b.po_number, b.spent - p.po_amount_usd AS amount_usd,
       printf('Spent $%,d on a $%,d PO (%d%%)', CAST(b.spent AS INT), CAST(p.po_amount_usd AS INT), CAST(100 * b.spent / p.po_amount_usd AS INT)) AS detail
FROM booked b JOIN stg_purchase_orders p ON p.po_number = b.po_number AND p.advertiser_id = b.advertiser_id
JOIN stg_advertisers a ON a.advertiser_id = b.advertiser_id
WHERE b.spent > p.po_amount_usd
UNION ALL
SELECT 'PO number on two advertisers', 'High', a.advertiser_id, a.advertiser_name, a.agency_name, p.po_number,
       p.po_amount_usd, 'Same PO number issued to another advertiser'
FROM stg_purchase_orders p JOIN stg_advertisers a USING (advertiser_id)
WHERE p.po_number IN (SELECT po_number FROM stg_purchase_orders GROUP BY po_number HAVING COUNT(DISTINCT advertiser_id) > 1)
UNION ALL
SELECT 'Spend on expired PO', 'Medium', a.advertiser_id, a.advertiser_name, a.agency_name, f.po_number,
       SUM(f.spend_usd), printf('%d weeks booked after the PO ended %s', COUNT(DISTINCT f.week_num), p.po_end)
FROM fct_spend f JOIN stg_purchase_orders p ON p.po_number = f.po_number AND p.advertiser_id = f.advertiser_id
JOIN stg_advertisers a ON a.advertiser_id = f.advertiser_id
WHERE f.week_start > p.po_end
GROUP BY a.advertiser_id, a.advertiser_name, a.agency_name, f.po_number, p.po_end
UNION ALL
SELECT 'Missing PO number', 'Medium', a.advertiser_id, a.advertiser_name, a.agency_name, NULL,
       SUM(f.spend_usd), printf('%d invoice-billed weeks with no PO', COUNT(DISTINCT f.week_num))
FROM fct_spend f JOIN stg_advertisers a ON a.advertiser_id = f.advertiser_id
WHERE f.billing_type = 'invoice' AND f.po_number IS NULL
GROUP BY a.advertiser_id, a.advertiser_name, a.agency_name
UNION ALL
SELECT 'No Q4 PO yet', 'Low', a.advertiser_id, a.advertiser_name, a.agency_name, NULL,
       q3.spend, 'Spending in September, no Q4 PO on file'
FROM (SELECT advertiser_id, SUM(spend_usd) AS spend FROM fct_spend WHERE quarter = '2026-Q3' GROUP BY advertiser_id
      HAVING SUM(CASE WHEN week_num >= 23 THEN spend_usd ELSE 0 END) > 0) q3
JOIN stg_advertisers a USING (advertiser_id)
WHERE a.billing_type = 'invoice'
  AND a.advertiser_id NOT IN (SELECT advertiser_id FROM stg_purchase_orders WHERE quarter = '2026-Q4');

-- Q3 delivery vs commitment.
DROP TABLE IF EXISTS mart_attainment;
CREATE TABLE mart_attainment AS
SELECT c.advertiser_id, a.advertiser_name, a.vertical, a.tier, a.csm_name, c.committed_usd,
       COALESCE(s.spend, 0) AS spend, COALESCE(s.spend, 0) / c.committed_usd AS attainment,
       CASE WHEN COALESCE(s.spend, 0) / c.committed_usd > 1.10 THEN 'Over'
            WHEN COALESCE(s.spend, 0) / c.committed_usd >= 0.90 THEN 'On plan'
            ELSE 'Under' END AS status
FROM raw_quarterly_commitments c
JOIN stg_advertisers a USING (advertiser_id)
LEFT JOIN (SELECT advertiser_id, SUM(spend_usd) AS spend FROM fct_spend WHERE quarter = '2026-Q3' GROUP BY advertiser_id) s USING (advertiser_id)
WHERE c.quarter = '2026-Q3';

-- The sales question: "Is Auto-Campaigns cheaper per conversion than In-Feed Video?"
-- All accounts mixes verticals (Auto-Campaigns adopters lean to Gaming and Retail, where conversions are cheap).
-- Like for like compares the two products inside the same account in the same week.
DROP TABLE IF EXISTS mart_cpa_question;
CREATE TABLE mart_cpa_question AS
WITH pairs AS (
  SELECT a.advertiser_id, a.week_num
  FROM fct_spend a JOIN fct_spend b ON b.advertiser_id = a.advertiser_id AND b.week_num = a.week_num
  WHERE a.product = 'Auto-Campaigns' AND b.product = 'In-Feed Video' AND a.quarter = '2026-Q3'
)
SELECT 'All accounts' AS comparison,
       SUM(CASE WHEN product = 'Auto-Campaigns' THEN spend_usd END) / SUM(CASE WHEN product = 'Auto-Campaigns' THEN conversions END) AS auto_cpa,
       SUM(CASE WHEN product = 'In-Feed Video' THEN spend_usd END) / SUM(CASE WHEN product = 'In-Feed Video' THEN conversions END) AS infeed_cpa,
       SUM(CASE WHEN product = 'Auto-Campaigns' AND vertical IN ('Gaming', 'Retail') THEN spend_usd END) / SUM(CASE WHEN product = 'Auto-Campaigns' THEN spend_usd END) AS auto_share_gaming_retail,
       SUM(CASE WHEN product = 'In-Feed Video' AND vertical IN ('Gaming', 'Retail') THEN spend_usd END) / SUM(CASE WHEN product = 'In-Feed Video' THEN spend_usd END) AS infeed_share_gaming_retail
FROM fct_spend WHERE quarter = '2026-Q3'
UNION ALL
SELECT 'Same account, same week',
       SUM(CASE WHEN f.product = 'Auto-Campaigns' THEN f.spend_usd END) / SUM(CASE WHEN f.product = 'Auto-Campaigns' THEN f.conversions END),
       SUM(CASE WHEN f.product = 'In-Feed Video' THEN f.spend_usd END) / SUM(CASE WHEN f.product = 'In-Feed Video' THEN f.conversions END),
       NULL, NULL
FROM fct_spend f JOIN pairs p ON p.advertiser_id = f.advertiser_id AND p.week_num = f.week_num
WHERE f.product IN ('Auto-Campaigns', 'In-Feed Video');

-- QBR account: product view by quarter.
DROP TABLE IF EXISTS mart_qbr;
CREATE TABLE mart_qbr AS
SELECT f.advertiser_id, f.advertiser_name, f.quarter, f.product, SUM(f.spend_usd) AS spend,
       SUM(f.impressions) AS impressions, SUM(f.clicks) AS clicks, SUM(f.conversions) AS conversions,
       SUM(f.conversion_value_usd) AS conversion_value
FROM fct_spend f WHERE f.advertiser_name = 'Maple & Main Grocers'
GROUP BY f.advertiser_id, f.advertiser_name, f.quarter, f.product;
