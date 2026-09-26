# Baseline pipeline report

## Source

| Field | Value |
| --- | --- |
| source | Crossref REST API |
| source_mode | local_raw_snapshot |
| query | agentic retrieval augmented generation large language model |
| filter | from-pub-date:2026-03-30,has-abstract:true |
| records | 24 |
| clean_records | 24 |
| raw_response_path | data/raw/crossref_response.json |
| raw_records_path | data/raw/crossref_records.json |
| collection_name | papers-baseline |
| run_started_at | 2026-09-26T05:54:14.344101+00:00 |

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
| ExpectColumnValuesToNotMatchRegex | summary | Yes |

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
