# Bảng Mapping: 6 Corruption Scenarios ↔ 4 Great Expectations

> **Mục đích:** File này là hợp đồng giữa Thái (Corruption Owner) và Dũng (Observability Owner).
> Khi Dũng viết `src/observability/quality.py::run_data_quality_checks()`, bảng này đảm bảo
> rằng 4 expectations của Dũng sẽ FAIL trên corrupted data và PASS trên baseline/repaired.
>
> **Quy ước trigger:** Một expectation **BẮT BUỘC FAIL** khi scenario tương ứng được kích hoạt.

---

## 1. Bảng ánh xạ chính

| # | Scenario (Thái) | Hàm `_apply_*` | Quality Signal mong đợi | GX Expectation (Dũng viết) | Trạng thái baseline → corrupted |
|:-:|---|---|---|---|---|
| 1 | `drop_latest_records` | `_apply_drop_latest` | `row_count_below_min` | `ExpectTableRowCountToBeBetween(min=20, max=30)` | PASS → FAIL |
| 2 | `blank_summary` | `_apply_blank_summary` | `null_summary_violation` | `ExpectColumnValuesToNotBeNull(column="summary")` | PASS → FAIL |
| 3 | `inject_noise` | `_apply_inject_noise` | `summary_length_above_max` | `ExpectColumnValueLengthsToBeBetween(column="summary", min=10, max=1000)` | PASS → PASS* |
| 4 | `truncate_title` | `_apply_truncate_title` | `title_length_below_min` | `ExpectColumnValueLengthsToBeBetween(column="title", min=8, max=300)` | PASS → FAIL |
| 5 | `stale_date` | `_apply_stale_date` | `freshness_sla_violation` | Freshness SLA (custom, không phải GX) | is_fresh=True → is_fresh=False |
| 6 | `duplicate_rows` | `_apply_duplicate_rows` | `paper_id_unique_violation` | `ExpectColumnValuesToBeUnique(column="paper_id")` | PASS → FAIL |

> **Ghi chú (*):** Scenario #3 (`inject_noise`) chỉ làm summary DÀI HƠN — không vượt max nếu max lớn.
> Nếu Dũng muốn catch scenario này bằng GX, set `max` thấp (ví dụ: 500). Hoặc để Dũng giữ max rộng
> và tập trung vào 4 expectation cốt lõi.

---

## 2. Chi tiết từng scenario → artifact

### Scenario 1: Drop latest records
```python
# Trong corrupt_clean_dataframe:
n_drop = max(1, int(len(df) * 0.2))   # 20% of 24 = ~5 rows
sorted_df = df.sort_values("published", ascending=False)
drop_ids = sorted_df.head(n_drop)["paper_id"].tolist()
corrupted = df[~df["paper_id"].isin(drop_ids)]
```
- **Record tác động:** 5 records có `published` mới nhất
- **Trước:** 24 rows → **Sau:** 19 rows
- **GX expectation:** `ExpectTableRowCountToBeBetween(min=20, max=30)`
  - Baseline: 24 ∈ [20,30] → PASS
  - Corrupted: 19 ∉ [20,30] → FAIL ✅

### Scenario 2: Blank summary
```python
target_count = 3
target_indices = RNG.sample(range(len(df)), k=target_count)
corrupted.loc[target, "summary"] = ""
```
- **Record tác động:** 3 records random
- **Trước:** `summary` ≠ null → **Sau:** `summary` = ""
- **GX expectation:** `ExpectColumnValuesToNotBeNull(column="summary")`
  - Baseline: 24/24 không null → PASS
  - Corrupted: 3/24 null → FAIL ✅

### Scenario 3: Inject noise
```python
noise = " ###CORRUPT### "
corrupted.loc[target, "summary"] = noise + summary + noise
```
- **Record tác động:** 3 records random
- **Trước:** summary ~200 chars → **Sau:** summary ~218 chars (+18 chars noise)
- **GX expectation:** Tùy chọn
  - Nếu set `ExpectColumnValueLengthsToBeBetween(max=500)`: PASS cả 2 trạng thái (không catch được)
  - Nếu set `max=210`: PASS baseline, FAIL corrupted ✅

### Scenario 4: Truncate title
```python
max_chars = 7
corrupted.loc[target, "title"] = title.str[:7]
```
- **Record tác động:** 2 records random
- **Trước:** title ~30+ chars → **Sau:** title 7 chars
- **GX expectation:** `ExpectColumnValueLengthsToBeBetween(column="title", min=8, max=300)`
  - Baseline: title ≥ 8 → PASS
  - Corrupted: title = 7 → FAIL ✅

### Scenario 5: Stale date
```python
days_back = 400  # > 180 ngưỡng Freshness
new_published = (run_date - timedelta(days=days_back)).date().isoformat()
corrupted.loc[target, "published"] = new_published
corrupted.loc[target, "age_days"] = days_back  # Recompute ngay
```
- **Record tác động:** 3 records random
- **Trước:** `age_days` ≤ 200 → **Sau:** `age_days` = 400
- **Freshness SLA (custom logic, không phải GX expectation):**
  ```python
  stale_ratio = (df["age_days"] > 180).sum() / len(df)
  is_fresh = stale_ratio <= 0.25
  ```
  - Baseline: stale_ratio ~0.5 (do fake data), `is_fresh` có thể False
  - Corrupted: stale_ratio tăng thêm do 3 record bị stale_date → `is_fresh = False`
  - Repaired (rebuild từ raw): `is_fresh` phụ thuộc raw data thực tế

### Scenario 6: Duplicate rows
```python
n_dup = 3
target_indices = RNG.sample(range(len(df)), k=n_dup)
duplicated = df.iloc[target_indices].copy()
corrupted = pd.concat([df, duplicated], ignore_index=True)
```
- **Record tác động:** 3 records bị duplicate
- **Trước:** 24 rows, paper_id unique → **Sau:** 27 rows, paper_id KHÔNG unique
- **GX expectation:** `ExpectColumnValuesToBeUnique(column="paper_id")`
  - Baseline: 24 unique → PASS
  - Corrupted: có 3 paper_id xuất hiện 2 lần → FAIL ✅

---

## 3. Bảng kỳ vọng baseline vs corrupted

| Expectation | Baseline (24 rows) | Corrupted (22-27 rows tùy combo) | Repaired (24 rows) |
|---|:---:|:---:|:---:|
| Row count ∈ [20,30] | ✅ PASS | ❌ FAIL | ✅ PASS |
| Summary not null | ✅ PASS | ❌ FAIL (3 blanks) | ✅ PASS |
| paper_id unique | ✅ PASS | ❌ FAIL (3 dups) | ✅ PASS |
| Title length ≥ 8 | ✅ PASS | ❌ FAIL (2 truncated) | ✅ PASS |
| `is_fresh` (Freshness SLA) | ✅ True* | ❌ False | ✅ True* |
| **TỔNG `success`** | **True** | **False** | **True** |

> (*) `is_fresh` phụ thuộc vào raw data thực tế. Với data Crossref mới nhất, baseline thường fresh.

---

## 4. Hợp đồng giữa Thái và Dũng

| Bên | Cam kết |
|---|---|
| **Thái (Corruption)** | ✅ Log file `data/results/corruption_log.json` ghi đầy đủ 6 scenarios với `expected_quality_signal` |
| **Thái (Corruption)** | ✅ Mỗi scenario có `affected_paper_ids` để debug khi GX fail |
| **Thái (Corruption)** | ✅ Repair rebuild từ `crossref_records.json` qua `build_clean_dataframe` — idempotent |
| **Dũng (Observability)** | ✅ Định nghĩa đúng 4 expectations mapping với scenarios #1, #2, #4, #6 |
| **Dũng (Observability)** | ✅ Tích hợp Freshness SLA với `is_fresh = False` khi `stale_ratio > 0.25` |
| **Dũng (Observability)** | ✅ Trả về payload có `success: bool` để Vinh pipeline so sánh 3 trạng thái |

---

## 5. Cách verify hợp đồng

Sau khi cả 2 bên hoàn thành, chạy:

```bash
python -c "
from core.config import load_settings
from observability.quality import run_data_quality_checks
from ingestion.corruption import corrupt_clean_dataframe
import pandas as pd
from datetime import datetime, timezone

s = load_settings()
df = pd.read_json(s.paths.clean_json)
run_date = datetime.now(timezone.utc)

# Baseline
r_baseline = run_data_quality_checks(df, s, 'baseline')
assert r_baseline['success'] is True, 'Baseline phai PASS'

# Corrupted
c = corrupt_clean_dataframe(df, s.paths.corruption_log, run_date=run_date)
r_corrupted = run_data_quality_checks(c, s, 'corrupted')
assert r_corrupted['success'] is False, 'Corrupted phai FAIL'
print('OK: Baseline PASS, Corrupted FAIL')
"
```

---

## 6. Lịch sử cập nhật

| Ngày | Người | Thay đổi |
|---|---|---|
| 2026-09-26 | Thái (2A202602407) | Khởi tạo bảng mapping sau khi implement `corruption.py` |
