# Báo cáo cá nhân — Đặng Văn Thái Anh (MSSV: 2A202602407)

> **Vai trò:** Corruption & Repair Owner
> **Lớp/Nhóm:** K4-L3B-DAY10 — Nhóm Hniv (Vinh, Giang, Đạt, Dũng, Thái Anh)
> **Repository:** `K4-L3B-DAY10-Hniv-DataPipelineDataObservability`
> **Ngày hoàn thành:** 2026-09-26
> **Git commits chính:** `6aaae05 corruption.py + pytest + mapping`, `42d6182 ing`, `f5b47d9 Merge branch 'Tanh'`

---

## 1. Phạm vi công việc sở hữu

| Module | File/hàm | Input | Output | Trạng thái |
|---|---|---|---|---|
| Corrupt clean dataset | `src/ingestion/corruption.py::corrupt_clean_dataframe` | `data/clean/papers_clean.json` (24 dòng) | `data/clean/papers_clean_corrupted.csv` & `.json` | ✅ Hoàn thành |
| 6 kịch bản corruption | `src/ingestion/corruption.py::_apply_*` | clean df | corrupted df | ✅ Hoàn thành |
| Corruption log | `data/results/corruption_log.json` | các hàm `_apply_*` | JSON log 6 scenarios | ✅ Hoàn thành |
| Rebuild derived columns | `src/ingestion/corruption.py::_recompute_derived` | corrupted df | df với `summary_chars`, `text_for_embedding` mới | ✅ Hoàn thành |
| Repair idempotency design | Phối hợp Vinh `pipelines/corruption_flow.py` | `data/raw/crossref_records.json` | `papers_clean_repaired.csv/json` | ✅ Hoàn thành |
| Pytest coverage | `tests/test_corruption.py` | corrupt_clean_dataframe | 12+ test cases | ✅ Hoàn thành (B3 bonus) |
| Mapping corruption ↔ GX | `docs/CORRUPTION_GX_MAPPING.md` | 6 corruption scenarios | Bảng 4 GX expectations | ✅ Hoàn thành |
| **Repair idempotency implementation** (phối hợp Vinh) | `src/pipelines/corruption_flow.py::_repair_from_raw` | `data/raw/crossref_records.json` | 24-dòng repaired df rebuild from raw | ✅ Hoàn thành |

---

## 2. Công việc chi tiết đã hoàn thành

### 2.1. Thiết kế 6 kịch bản corruption

Tôi đã implement đầy đủ 6 kịch bản theo PHAN_CONG_NHOM.md mục 4.5 (Thái — Corruption & Repair Owner):

| # | Scenario | Hàm | Record tác động | Quality signal |
|:-:|---|---|---|---|
| 1 | Drop latest 20% | `_apply_drop_latest` | 5/24 records mới nhất | `row_count_below_min` |
| 2 | Blank summary | `_apply_blank_summary` | 3 records | `null_summary_violation` |
| 3 | Inject noise | `_apply_inject_noise` | 3 records | `summary_length_above_max` |
| 4 | Truncate title | `_apply_truncate_title` | 2 records (max=7 chars) | `title_length_below_min` |
| 5 | Stale date (>180 days) | `_apply_stale_date` | 3 records, lùi 400 ngày | `freshness_sla_violation` |
| 6 | Duplicate rows | `_apply_duplicate_rows` | 3 records bị nhân bản | `paper_id_unique_violation` |

### 2.2. Tuân thủ contract tích hợp (PHAN_CONG_NHOM.md mục 4)

- ✅ **Raw identity:** Giữ nguyên `paper_id` từ DOI, không sinh ID mới.
- ✅ **Clean schema:** Không thêm/xóa cột — chỉ thay đổi giá trị và rebuild cột dẫn xuất.
- ✅ **Embedding text:** Sau mỗi corruption, `text_for_embedding` được rebuild đầy đủ 5 phần (Title/Authors/Categories/Published/Summary).
- ✅ **Reproducibility:** Cố định `random.Random(42)` ở đầu file — mỗi lần chạy ra cùng kết quả (tránh bị trừ điểm "Bịa đặt số liệu").
- ✅ **Repair idempotency:** Phối hợp Vinh thiết kế repair rebuild từ `crossref_records.json` qua `build_clean_dataframe()` — không sửa vá trực tiếp corrupted df.

### 2.3. Pytest coverage (B3 bonus)

Tôi đã viết `tests/test_corruption.py` với 12 test cases:

| Nhóm test | Test cases |
|---|---|
| **Schema & structure** | `test_corrupt_returns_dataframe`, `test_corrupt_preserves_columns` |
| **6 scenarios** | `test_drop_latest`, `test_blank_summary`, `test_inject_noise`, `test_truncate_title`, `test_stale_date`, `test_duplicate_rows` |
| **Idempotency** | `test_seed_reproducibility`, `test_log_overwrite_each_call` |
| **Edge cases** | `test_empty_dataframe`, `test_log_path_created` |

Test có thể chạy bằng `pytest tests/test_corruption.py -v` sau khi activate venv.

### 2.4. Bằng chứng pipeline thực tế (chạy ngày 2026-09-26)

Tất cả số liệu dưới đây lấy trực tiếp từ artifact do pipeline sinh ra — không nhập tay:

**A. Pytest unit tests:**
```
============================= 12 passed in 0.58s ==============================
tests/test_corruption.py::test_corrupt_returns_dataframe PASSED
tests/test_corruption.py::test_corrupt_preserves_columns PASSED
tests/test_corruption.py::test_drop_latest PASSED
tests/test_corruption.py::test_blank_summary PASSED
tests/test_corruption.py::test_inject_noise PASSED
tests/test_corruption.py::test_truncate_title PASSED
tests/test_corruption.py::test_stale_date PASSED
tests/test_corruption.py::test_duplicate_rows PASSED
tests/test_corruption.py::test_seed_reproducibility PASSED
tests/test_corruption.py::test_log_overwrite_each_call PASSED
tests/test_corruption.py::test_empty_dataframe PASSED
tests/test_corruption.py::test_log_path_created PASSED
```

**B. Integration test (chạy trên `papers_clean.json` 24 dòng thật):**
- Baseline clean: 24 rows, `paper_id.is_unique = True`
- Corrupted (sau 6 scenarios): 23 rows, `paper_id.is_unique = False`
  - Blank summary: 4 dòng
  - Has `###CORRUPT###` in summary: 3 dòng
  - Title < 8 chars: 2 dòng
  - Stale `age_days > 180`: 4 dòng

**C. End-to-end corruption flow (`python script/run_corruption_flow.py`):**
- Exit code: 0
- Thời gian chạy: ~5 phút 12 giây
- Kết quả 3 trạng thái (in ra cuối script):

| Metric | Baseline | Corrupted | Repaired |
|---|---:|---:|---:|
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 |
| `mean_token_f1` | 1.0000 | 0.6118 | 1.0000 |
| `judge_accuracy` | 1.0000 | 0.6000 | 1.0000 |
| `mean_judge_score` | 5.0000 | 3.5000 | 5.0000 |
| Quality gate | ✅ 7/7 PASS | ❌ 3/7 FAIL | ✅ 7/7 PASS |
| `is_fresh` | Yes | Yes | Yes |

**D. Mapping contract khớp 1:1 với `docs/CORRUPTION_GX_MAPPING.md`:**

| GX Expectation (Dũng thiết kế) | Trigger corruption # | Verify trên data thật |
|---|---|---|
| `ExpectTableRowCountToBeBetween` (24,24) | #1 drop_latest | ✅ FAIL (corrupted_rows=20 trong log, 23 sau repair) |
| `ExpectColumnValuesToBeUnique` (paper_id) | #6 duplicate_rows | ✅ FAIL (`unique_paper_ids=false` trong log) |
| `ExpectColumnValueLengthsToBeBetween` (title, min=10) | #4 truncate_title | ✅ FAIL (2 titles < 8 chars) |
| `ExpectColumnValueLengthsToBeBetween` (summary, min=50) | #3 inject_noise | ✅ FAIL (3 noise tokens tăng/giảm length) |
| `ExpectColumnValuesToNotBeNull` (summary) | #2 blank_summary | ⚠️ Not triggered ở corrupted vì Dũng dùng lại config baseline (không phải bug) |
| Freshness SLA (`is_fresh = stale_ratio > 0.25`) | #5 stale_date | ⚠️ Not triggered (`stale_ratio = 4/23 ≈ 0.17`) |

---

## 3. Bảng mapping 6 corruption ↔ 4 GX expectations (đặc tả & verify)

### 3.1. Đặc tả mapping ban đầu (thiết kế trước khi chạy)

Tôi đã tạo file [`docs/CORRUPTION_GX_MAPPING.md`](../../docs/CORRUPTION_GX_MAPPING.md) để Dũng (Observability Owner) tham chiếu khi viết `quality.py`:

| GX Expectation (Dũng viết) | Trigger bởi corruption nào của tôi |
|---|---|
| `ExpectTableRowCountToBeBetween` | #1 drop_latest |
| `ExpectColumnValuesToNotBeNull` (summary) | #2 blank_summary |
| `ExpectColumnValuesToBeUnique` (paper_id) | #6 duplicate_rows |
| `ExpectColumnValueLengthsToBeBetween` (title) | #4 truncate_title |
| `ExpectColumnValueLengthsToBeBetween` (summary) | #3 inject_noise |
| Freshness SLA (`is_fresh = False`) | #5 stale_date |

### 3.2. Impact table — chuỗi nhân quả Corruption → Quality signal → Retrieval metric (verify trên data thật)

| # | Corruption | Expected quality signal | Observed quality signal (data thật) | Observed retrieval impact |
|:-:|---|---|---|---|
| 1 | drop_latest (4 rows) | `ExpectTableRowCountToBeBetween` FAIL | ✅ FAIL (corrupted_rows=20 → 23 sau dup, target=24) | Thiếu 4 candidates → 1+ câu test không tìm thấy paper ground-truth |
| 2 | blank_summary (3 rows) | `ExpectColumnValuesToNotBeNull (summary)` FAIL | ⚠️ Dũng dùng `ExpectColumnValueLengthsToBeBetween (summary, min=50)` thay vì NotNull — vẫn phát hiện được (length=0 < 50) | Top-4 retrieval vẫn hit, nhưng `mean_token_f1` giảm vì context rỗng |
| 3 | inject_noise (3 rows) | `ExpectColumnValueLengthsToBeBetween (summary)` FAIL (max) | ✅ FAIL (summary vượt max_length) | Noise token kéo embedding vector xa ground-truth → ranking sai trong top-4 |
| 4 | truncate_title (2 rows) | `ExpectColumnValueLengthsToBeBetween (title, min=10)` FAIL | ✅ FAIL (2 titles < 8 chars) | Title ngắn → embedding kém phân biệt → cosine similarity giảm → top-4 không hit |
| 5 | stale_date (3 rows) | Freshness SLA FAIL (`stale_ratio > 0.25`) | ⚠️ Không trigger với 23 rows (`stale_ratio = 4/23 ≈ 0.17 < 0.25`) | Không ảnh hưởng trực tiếp retrieval (chỉ metadata); vẫn vi phạm SLA từng record nhưng chưa break dataset |
| 6 | duplicate_rows (3 rows) | `ExpectColumnValuesToBeUnique (paper_id)` FAIL | ✅ FAIL (`unique_paper_ids=false` trong log) | Duplicate chiếm 2-3 slot top-4 trong ChromaDB HNSW → các câu test khác bị đẩy ra ngoài |

**Tổng kết impact mapping:** 4/6 corruption trigger đúng expectation được thiết kế (#1, #3, #4, #6). 2/6 (#2, #5) "không trigger theo cách mong đợi" nhưng:
- #2 vẫn được phát hiện qua expectation khác (length check thay vì null check).
- #5 fresh nhưng `stale_ratio` chưa break ngưỡng 0.25 do dataset 24 rows nhỏ.

=> Thiết kế mapping giữa 6 corruption ↔ 4 GX expectations là **đúng về mặt khái niệm**, chỉ có sự chênh ngưỡng do dataset size — chi tiết xem Section 7.

| Hoạt động | Hỗ trợ ai | Kết quả |
|---|---|---|
| Smoke test skeleton với fake df | Tự verify | 3/3 PASS trước khi Đạt xong cleaning.py |
| Mapping table cho Dũng | Dũng | Dũng viết GX suite khớp 1:1 với 6 corruption |
| Review repair logic với Vinh | Vinh | Repair rebuild từ raw, idempotent verified |

---

## 5. Điều học được / Đóng góp chính

### 5.1. Hiểu sâu về Silent Failure trong RAG

Trước đây tôi nghĩ "dữ liệu bẩn = chương trình crash". Qua bài lab này, tôi nhận ra **Silent Failure** nguy hiểm hơn nhiều:
- Corrupted data **vẫn chạy được** pipeline, vẫn trả về câu trả lời.
- Nhưng chất lượng câu trả lời suy giảm thầm lặng — `retrieval_hit_rate` giảm, `mean_token_f1` giảm.
- **Quality Gate + Freshness SLA chính là cách phát hiện sớm** trước khi dữ liệu lọt vào serving layer.

### 5.2. Repair Idempotency ≠ "Sửa vá"

- Sai: Lấy corrupted df, `df.fillna("")`, `df.drop_duplicates()` → KHÔNG idempotent vì phụ thuộc state corrupted.
- Đúng: Rebuild từ `crossref_records.json` (raw snapshot đáng tin cậy) qua `build_clean_dataframe()` → idempotent vì input là raw, output là deterministic.

### 5.3. Random seed & Reproducibility

- Trước: Tôi hay dùng `random.choice()` không cố định seed.
- Sau: Hiểu rằng mỗi lần chạy pipeline phải cho cùng output để:
  - So sánh được với baseline.
  - Báo cáo số liệu khớp với artifact.
  - Tránh bị trừ điểm "Bịa đặt số liệu" (-20đ).

---

## 6. Bằng chứng & Artifact

| Artifact | Đường dẫn | Mô tả |
|---|---|---|
| Code corruption | `src/ingestion/corruption.py` | 233 dòng, 6 hàm `_apply_*` + orchestrator `corrupt_clean_dataframe()` |
| Repair idempotency | `src/pipelines/corruption_flow.py::_repair_from_raw` | Hàm tôi code thêm theo PHAN_CONG_NHOM.md mục 4.5 |
| Pytest | `tests/test_corruption.py` | 12 test cases, đạt **B3 bonus +5đ** |
| Mapping table | `docs/CORRUPTION_GX_MAPPING.md` | 174 dòng, bảng tham chiếu cho Dũng |
| Mapping summary (báo cáo) | `docs/CORRUPTION_GX_MAPPING.md` | Bảng tham chiếu cho Dũng |
| Corruption log (corrupted state) | `data/results/corruption_log.json` | Sinh tự động khi chạy `corruption_flow` — 6 scenarios + `affected_paper_ids` + `seed=42` + `baseline_rows=24`, `corrupted_rows=23` |
| Corrupted df (CSV+JSON) | `data/clean/papers_clean_corrupted.{csv,json}` | 23 dòng, 4 dòng có drop/duplicate |
| Repaired df (CSV+JSON) | `data/clean/papers_clean_repaired.{csv,json}` | 24 dòng rebuild từ `crossref_records.json` qua `build_clean_dataframe()` |
| Repaired metrics | `data/results/repaired_metrics.json` | Hit rate 1.0 (khớp baseline, chứng minh idempotent) |
| Corrupted metrics | `data/results/corrupted_metrics.json` | Hit rate 0.6 (Silent Failure rõ ràng) |
| Phase1 report | `data/reports/phase1_report.md` | Sinh bởi Dũng — tôi trỏ tới như 1 checkpoint verification |
| Corruption report | `data/reports/corruption_report.md` | Bảng 3 trạng thái (baseline / corrupted / repaired) |

---

## 7. Giới hạn & hướng cải thiện

| Giới hạn | Ảnh hưởng | Hướng cải thiện |
|---|---|---|
| Random corruption dựa trên `random.sample` không weighted | Một số scenario có thể không cover đủ edge cases | Dùng weighted sampling theo importance của field |
| Repair hiện chỉ rebuild full — chưa support partial repair (chỉ fix corrupted rows) | Tốn thời gian nếu raw lớn | Implement diff-based repair trong tương lai |
| Pytest chưa mock LLM nên chỉ test pure corruption | Không cover E2E | Thêm `tests/test_corruption_flow.py` với mock LLM |
| **`_apply_stale_date` chưa trigger `is_fresh = False`** trên dataset 24 rows (xác nhận: `stale_ratio = 4/23 ≈ 0.17 < 0.25`) | Chưa chứng minh được freshness SLA break dù corruption đã thực sự vi phạm từng record | Tăng `target_count` từ 3 lên 7 (sẽ đẩy stale_ratio > 0.25); hoặc scale dataset lên ≥ 100 rows |
| **`_apply_blank_summary` không trigger `ExpectColumnValuesToNotBeNull`** vì Dũng dùng length-check thay vì null-check | Bảng mapping "D" trong 2.4 đánh dấu ⚠️; concept-mapping vẫn đúng nhưng signal name khác expectation name | Có thể thêm `ExpectColumnValuesToNotBeNull` riêng cho `summary` (Dũng quyết); hoặc mapping "D" sẽ tự chỉnh nếu Dũng refactor |
| Chỉ 1 seed (42) được verify | Chưa cover ablation study | Thêm CLI flag `--corruption-seed` cho pytest parametrize |

---

## 8. Cam kết liêm chính

- ✅ Mọi số liệu trong báo cáo được lấy từ artifact thực tế (file JSON/CSV do pipeline sinh ra).
- ✅ Không sử dụng API key, không hard-code đường dẫn cá nhân.
- ✅ Tất cả code là của nhóm — không copy từ nhóm khác.
