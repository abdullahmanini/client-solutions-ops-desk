-- Staging: clean, typed, de-duplicated copies of the raw exports.

DROP TABLE IF EXISTS stg_advertisers;
CREATE TABLE stg_advertisers AS
SELECT a.advertiser_id, a.advertiser_name, a.vertical, a.tier, a.market, a.agency_id,
       ag.agency_name, a.csm_id, c.csm_name, a.billing_type, a.account_type,
       CASE WHEN a.account_type = 'internal_test' THEN 1 ELSE 0 END AS is_test
FROM raw_advertisers a
LEFT JOIN raw_agencies ag ON ag.agency_id = a.agency_id
LEFT JOIN raw_csms c ON c.csm_id = a.csm_id;

-- The week-17 US export was loaded twice (load 1017 and load 2017). Keep the latest load per key.
DROP TABLE IF EXISTS stg_ad_spend;
CREATE TABLE stg_ad_spend AS
WITH ranked AS (
  SELECT r.*,
         ROW_NUMBER() OVER (PARTITION BY week_start, advertiser_id, product ORDER BY load_id DESC) AS rn
  FROM raw_ad_spend_export r
)
SELECT week_start,
       CAST((julianday(week_start) - julianday('2026-04-06')) / 7 AS INTEGER) + 1 AS week_num,
       CASE WHEN week_start < '2026-07-06' THEN '2026-Q2' ELSE '2026-Q3' END AS quarter,
       advertiser_id, product, spend_usd, impressions, clicks, conversions, conversion_value_usd,
       NULLIF(po_number, '') AS po_number
FROM ranked
WHERE rn = 1;

DROP TABLE IF EXISTS stg_purchase_orders;
CREATE TABLE stg_purchase_orders AS
SELECT po_number, advertiser_id, agency_id, quarter, po_start, po_end, po_amount_usd
FROM raw_purchase_orders;

-- Reporting fact: client accounts only (internal QA sandboxes excluded).
DROP TABLE IF EXISTS fct_spend;
CREATE TABLE fct_spend AS
SELECT s.*, a.advertiser_name, a.vertical, a.tier, a.market, a.agency_id, a.agency_name,
       a.csm_id, a.csm_name, a.billing_type
FROM stg_ad_spend s
JOIN stg_advertisers a ON a.advertiser_id = s.advertiser_id
WHERE a.is_test = 0;
