# Corruption and repair report

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| retrieval_hit_rate | 1.0000 | 0.6000 | 1.0000 |
| mean_token_f1 | 1.0000 | 0.6118 | 1.0000 |
| judge_accuracy | 1.0000 | 0.6000 | 1.0000 |
| mean_judge_score | 5 | 3.4000 | 5 |

## Quality and freshness

| Signal | Corrupted | Repaired |
| --- | ---: | ---: |
| Quality gate | No (3/7 checks) | Yes (7/7 checks) |
| Failed checks | ExpectTableRowCountToBeBetween (table), ExpectColumnValuesToBeUnique (paper_id), ExpectColumnValueLengthsToBeBetween (title), ExpectColumnValueLengthsToBeBetween (summary) | None |
| is_fresh | No | Yes |
| stale_rows | 7 | 0 |
| total_rows | 23 | 24 |
| stale_ratio | 0.3043 | 0.0000 |
| latest_published | 2026-08-27 | 2026-09-15 |
| oldest_published | 2025-08-22 | 2026-04-01 |

## Observed changes

- retrieval_hit_rate: corrupted − baseline = -0.4000; repaired − corrupted = 0.4000.
- mean_token_f1: corrupted − baseline = -0.3882; repaired − corrupted = 0.3882.
- judge_accuracy: corrupted − baseline = -0.4000; repaired − corrupted = 0.4000.
- mean_judge_score: corrupted − baseline = -1.6000; repaired − corrupted = 1.6000.
