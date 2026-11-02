-- Data tests. Each row: test id, layer, what it checks, severity, number of failing rows.
-- error = the number cannot be reported until fixed; warn = goes to the exceptions queue.

DROP TABLE IF EXISTS test_results;
CREATE TABLE test_results AS
SELECT 'T01' AS test_id, 'raw' AS layer, 'Export has one row per week, advertiser and product' AS description, 'error' AS severity,
       (SELECT COUNT(*) FROM (SELECT 1 FROM raw_ad_spend_export GROUP BY week_start, advertiser_id, product HAVING COUNT(*) > 1)) AS failures
UNION ALL SELECT 'T02', 'staging', 'Staged spend has one row per week, advertiser and product', 'error',
       (SELECT COUNT(*) FROM (SELECT 1 FROM stg_ad_spend GROUP BY week_start, advertiser_id, product HAVING COUNT(*) > 1))
UNION ALL SELECT 'T03', 'staging', 'Spend is positive', 'error',
       (SELECT COUNT(*) FROM stg_ad_spend WHERE spend_usd <= 0 OR spend_usd IS NULL)
UNION ALL SELECT 'T04', 'staging', 'Clicks never exceed impressions', 'error',
       (SELECT COUNT(*) FROM stg_ad_spend WHERE clicks > impressions)
UNION ALL SELECT 'T05', 'staging', 'Conversions never exceed clicks', 'error',
       (SELECT COUNT(*) FROM stg_ad_spend WHERE conversions > clicks)
UNION ALL SELECT 'T06', 'staging', 'Every spend row maps to a known advertiser', 'error',
       (SELECT COUNT(*) FROM stg_ad_spend s LEFT JOIN stg_advertisers a USING (advertiser_id) WHERE a.advertiser_id IS NULL)
UNION ALL SELECT 'T07', 'staging', 'Weeks start on a Monday inside the reporting window', 'error',
       (SELECT COUNT(*) FROM stg_ad_spend WHERE strftime('%w', week_start) <> '1' OR week_num NOT BETWEEN 1 AND 26)
UNION ALL SELECT 'T08', 'staging', 'Every product is in the product catalogue', 'error',
       (SELECT COUNT(*) FROM stg_ad_spend s LEFT JOIN raw_products p USING (product) WHERE p.product IS NULL)
UNION ALL SELECT 'T09', 'staging', 'No Auto-Campaigns spend before launch', 'error',
       (SELECT COUNT(*) FROM stg_ad_spend s JOIN raw_products p USING (product) WHERE s.week_start < p.launch_week_start)
UNION ALL SELECT 'T10', 'staging', 'Sandbox-named accounts are flagged as internal tests', 'error',
       (SELECT COUNT(*) FROM stg_advertisers WHERE advertiser_name LIKE 'QA Sandbox%' AND is_test = 0)
UNION ALL SELECT 'T11', 'reporting', 'Reporting fact excludes internal test accounts', 'error',
       (SELECT COUNT(*) FROM fct_spend f JOIN stg_advertisers a USING (advertiser_id) WHERE a.is_test = 1)
UNION ALL SELECT 'T12', 'staging', 'Each PO number belongs to one advertiser', 'warn',
       (SELECT COUNT(*) FROM (SELECT po_number FROM stg_purchase_orders GROUP BY po_number HAVING COUNT(DISTINCT advertiser_id) > 1))
UNION ALL SELECT 'T13', 'staging', 'Invoice-billed spend carries a PO number', 'warn',
       (SELECT COUNT(*) FROM fct_spend WHERE billing_type = 'invoice' AND po_number IS NULL)
UNION ALL SELECT 'T14', 'staging', 'Spend falls inside the dates of the PO it is booked to', 'warn',
       (SELECT COUNT(*) FROM fct_spend f JOIN stg_purchase_orders p ON p.po_number = f.po_number AND p.advertiser_id = f.advertiser_id
         WHERE f.week_start > p.po_end OR f.week_start < p.po_start)
UNION ALL SELECT 'T15', 'staging', 'Spend booked to a PO stays within the PO amount', 'warn',
       (SELECT COUNT(*) FROM (SELECT f.po_number, f.advertiser_id, SUM(f.spend_usd) AS spent, MAX(p.po_amount_usd) AS amt
                              FROM fct_spend f JOIN stg_purchase_orders p ON p.po_number = f.po_number AND p.advertiser_id = f.advertiser_id
                              GROUP BY 1, 2 HAVING spent > amt))
UNION ALL SELECT 'T16', 'raw', 'Weekly client spend moves less than 25% week over week', 'warn',
       (SELECT COUNT(*) FROM (
          SELECT week_start, SUM(r.spend_usd) AS s, LAG(SUM(r.spend_usd)) OVER (ORDER BY week_start) AS prev
          FROM raw_ad_spend_export r JOIN stg_advertisers a USING (advertiser_id) WHERE a.is_test = 0
          GROUP BY week_start) WHERE prev IS NOT NULL AND ABS(s / prev - 1) > 0.25)
UNION ALL SELECT 'T17', 'reporting', 'Weekly client spend moves less than 25% week over week', 'warn',
       (SELECT COUNT(*) FROM (
          SELECT week_start, SUM(spend_usd) AS s, LAG(SUM(spend_usd)) OVER (ORDER BY week_start) AS prev
          FROM fct_spend GROUP BY week_start) WHERE prev IS NOT NULL AND ABS(s / prev - 1) > 0.25);
