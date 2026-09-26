# Baseline pipeline report

## Source

| Field | Value |
| --- | --- |
| source | Crossref REST API |
| raw_response_status | ok |
| raw_response_items | 24 |
| raw_records | 24 |
| clean_records | 24 |
| raw_response_path | data\raw\crossref_response.json |
| raw_records_path | data\raw\crossref_records.json |
| clean_data_path | data\clean\papers_clean.json |

## Evaluation

| Metric | Value |
| --- | ---: |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 1.0000 |
| judge_accuracy | 1.0000 |
| mean_judge_score | 5 |

## Data quality

Overall gate: **Yes**

| Check | Column | Passed |
| --- | --- | --- |
| ExpectTableRowCountToBeBetween | N/A | Yes |
| ExpectColumnValuesToNotBeNull | paper_id | Yes |
| ExpectColumnValuesToNotBeNull | title | Yes |
| ExpectColumnValuesToNotBeNull | summary | Yes |
| ExpectColumnValuesToBeUnique | paper_id | Yes |
| ExpectColumnValueLengthsToBeBetween | title | Yes |
| ExpectColumnValueLengthsToBeBetween | summary | Yes |

Failed checks: None

## Freshness

| Signal | Value |
| --- | ---: |
| latest_published | 2026-09-15 |
| oldest_published | 2026-04-01 |
| stale_rows | 0 |
| total_rows | 24 |
| stale_ratio | 0.0000 |
| freshness_threshold_days | 180 |
| stale_ratio_threshold | 0.2500 |
| is_fresh | Yes |
