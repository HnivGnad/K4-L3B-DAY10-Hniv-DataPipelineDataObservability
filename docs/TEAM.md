# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Hniv` (5 thành viên)
- **Mã Nhóm / Lớp:** `K4-L3B-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3B-DAY10-Hniv-DataPipelineDataObservability`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Đặng Thế Vinh | `2A202602587` | `vjnhdang03@gmail.com` | Trưởng nhóm / Pipeline Integration & Evidence Owner — `src/pipelines/phase1.py`, tích hợp end-to-end, cấu hình, metrics, bằng chứng nghiệm thu | `report/report/2A202602587_DangTheVinh.md` |
| 2 | Nguyễn Thanh Giang | `2A202602576` | `giang1462004@gmail.com` | Source & Data Lineage Owner — `src/ingestion/crossref.py`, parse Crossref, retry/backoff, raw response, raw records | `report/2A202602576_NguyenThanhGiang.md` ✅ |
| 3 | Nguyễn Tất Đạt | `2A202602578` | `dat111104@gmail.com` | Cleaning & Evaluation-set Owner — `src/ingestion/cleaning.py`, `src/evaluation/testset.py`, cleaned dataset, `text_for_embedding` 5 phần, test set 10 câu; hỗ trợ rà soát tích hợp | `report/2A202602578_NguyenTatDat.md` ✅ |
| 4 | Hoàng Quốc Dũng | `2A202602523` | `quocdung.work99@gmail.com` | Data Observability & Reporting Owner — `src/observability/quality.py`, `src/observability/reporting.py`, GX 1.x ephemeral context, Freshness SLA, Markdown reports | `report/2A202602523_HoangQuocDung.md` |
| 5 | **Đặng Văn Thái Anh** | **`2A202602407`** | `danganh01032004@gmail.com` | Corruption & Repair Owner — `src/ingestion/corruption.py`, 6 corruption scenarios, `data/results/corruption_log.json`, kiểm chứng corrupted/repaired, repair idempotent từ raw records, thiết kế mapping corruption ↔ GX expectations | `report/2A202602407_DangVanThaiAnh.md` ✅ |


---

## # Cam kết đóng góp (dựa trên Git history & artifacts)

| Thành viên | Commit chính (trên nhánh `main`) | Module chịu trách nhiệm | Bằng chứng |
|---|---|---|---|
| Đặng Thế Vinh | `69257f2 baseline index + evaluation` | `src/pipelines/phase1.py` | `data/results/baseline_metrics.json`, `data/chroma/` |
| Nguyễn Thanh Giang | `ddcd76b complete crossref ingestion` | `src/ingestion/crossref.py` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| Nguyễn Tất Đạt | `e590b6d Tat Dat done step 2`, `94c362f CLEAN SCHEMA`, `10895d9 Tat dat final` | Sở hữu `src/ingestion/cleaning.py`, `src/evaluation/testset.py`; hỗ trợ rà soát tích hợp trong `10895d9` | `data/clean/papers_clean.json`, `data/eval/test_set.json`, `docs/CLEAN_SCHEMA.md`, `report/2A202602578_NguyenTatDat.md` |
| Hoàng Quốc Dũng | `e6c4662 Add Dung observability and baseline reports`, `8cc8cd5 Merge branch feature/2A202602523-dung-observability` | `src/observability/quality.py`, `src/observability/reporting.py` | `data/quality/*.json`, `data/reports/*.md` |
| Đặng Văn Thái Anh | `6aaae05 corruption.py + pytest + mapping`, `42d6182 ing`, `f5b47d9 Merge branch 'Tanh'` | `src/ingestion/corruption.py`, hỗ trợ `src/pipelines/corruption_flow.py` | `data/results/corruption_log.json`, `data/clean/papers_clean_corrupted.*`, `data/clean/papers_clean_repaired.*`, `data/results/{corrupted,repaired}_metrics.json`, `tests/test_corruption.py`, `docs/CORRUPTION_GX_MAPPING.md` |

---

## # Cá nhân

### ## Đặng Thế Vinh - 2A202602587 (Trưởng nhóm)
- **Vai trò:** Pipeline Integration & Evidence Owner.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình `core/config.py` với paths cho 3 trạng thái (baseline/corrupted/repaired) + LLM providers.
  - Xây dựng `src/pipelines/phase1.py::run_baseline()` end-to-end: load raw → clean → ChromaDB → evaluate → quality → report.
  - Verify baseline `retrieval_hit_rate = 1.0` trên 10 câu test, quality gate pass 7/7 checks.
  - Điều phối review chéo giữa các thành viên.
- **Điều học được / Đóng góp chính:**
  - Hiểu sâu thiết kế Idempotent Pipeline với 3 collection ChromaDB tách biệt để so sánh khách quan.

### ## Nguyễn Thanh Giang — 2A202602576
- **Vai trò:** Source & Data Lineage Owner.
- **Công việc chi tiết đã hoàn thành:**
  - `src/ingestion/crossref.py`: parse `payload["message"]["items"]` → list `PaperRecord` với DOI làm `paper_id` ổn định.
  - `fetch_source_records()`: retry/backoff cho HTTP 429/503 với `time.sleep(2**attempt)`, fallback đọc `crossref_response.json` local khi API lỗi.
  - `load_raw_records()` đọc `crossref_records.json` map ngược về `PaperRecord`.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage) — bảo toàn raw snapshot trước khi biến đổi, fallback offline đảm bảo reproducibility.

### ## Nguyễn Tất Đạt — 2A202602578
- **Vai trò:** Cleaning & Evaluation-set Owner.
- **Công việc chi tiết đã hoàn thành:**
  - `src/ingestion/cleaning.py`: bỏ JATS XML tag bằng `re.sub(r"<[^>]*>", " ")`, parse `published` qua `pd.to_datetime`, tính `age_days = (run_day - published).days`, infer topic từ title khi thiếu `subject`, dedupe theo `paper_id`.
  - `build_embedding_text()`: cấu trúc 5 phần `Title / Summary / Authors / Categories / Published`.
  - `src/evaluation/testset.py::build_test_set()`: 10 câu theo 4 loại (summary/authors/date/categories), chọn paper có title sạch (không có `'`), `ground_truth_doc_ids` trỏ đúng 1 paper.
  - `docs/CLEAN_SCHEMA.md`: ghi contract clean schema và nguồn `category_source=title_rules` cho snapshot không có Crossref subject.
  - Commit `10895d9`: hỗ trợ rà soát evaluation dùng semantic retrieval, đồng bộ corruption/quality gate, Auto-Repair và UI; chi tiết phạm vi và bằng chứng nằm trong báo cáo cá nhân.
- **Điều học được / Đóng góp chính:**
  - Cách thiết kế clean schema ổn định cho cả 3 trạng thái và test set deterministic với paper_id không trùng.

### ## Hoàng Quốc Dũng
- **Vai trò:** Data Observability & Reporting Owner.
- **Công việc chi tiết đã hoàn thành:**
  - `src/observability/quality.py`: Great Expectations **1.x** đúng chuẩn (`gx.get_context(mode="ephemeral")` + `data_sources.add_pandas` + `dataframe_asset` + `batch_definition_whole_dataframe`).
  - 7 expectations: row count, paper_id/title/summary not null, paper_id unique, title/summary length.
  - `build_freshness_report()`: `stale_rows`, `stale_ratio`, `is_fresh = stale_ratio <= 0.25`.
  - `src/observability/reporting.py`: render Markdown cho `phase1_report.md` (Source/Eval/Quality/Freshness) + `corruption_report.md` (bảng 3 cột Baseline/Corrupted/Repaired + Observed changes).
- **Điều học được / Đóng góp chính:**
  - Cách thiết lập hệ thống cảnh báo sớm chặn đứng hiện tượng Silent Failure trước khi dữ liệu vào serving layer.

### ## Đặng Văn Thái Anh — 2A202602407 (Corruption & Repair Owner)
- **Vai trò:** Corruption & Repair Owner.
- **Công việc chi tiết đã hoàn thành:**
  - `src/ingestion/corruption.py::corrupt_clean_dataframe()`: 6 scenario với `RNG = random.Random(42)` cố định để reproducible.
    - `_apply_drop_latest` — drop 20% (4 rows) records mới nhất.
    - `_apply_blank_summary` — 3 dòng `summary = ""`.
    - `_apply_inject_noise` — chèn `###CORRUPT###` vào 3 summary.
    - `_apply_truncate_title` — cắt title ≤ 7 chars (2 dòng).
    - `_apply_stale_date` — lùi `published` về 400 ngày trước (3 dòng) + recompute `age_days`.
    - `_apply_duplicate_rows` — `pd.concat` 3 dòng duplicate.
  - `_recompute_derived()` rebuild `summary_chars` + `text_for_embedding` sau corrupt.
  - `data/results/corruption_log.json`: ghi đầy đủ 6 scenarios với `affected_paper_ids`, `expected_quality_signal`, `baseline_rows=24`, `corrupted_rows=23`, `unique_paper_ids=false`.
  - Phối hợp Vinh thiết kế `_repair_from_raw()` trong `src/pipelines/corruption_flow.py`: rebuild từ `crossref_records.json` qua `build_clean_dataframe()` — idempotent, không sửa trực tiếp corrupted.
  - `tests/test_corruption.py`: 12 test cases (schema, 6 scenarios, idempotency, edge cases) — **12/12 PASS** trong 0.58s (đạt **B3 bonus +5đ** Pytest CI).
  - `docs/CORRUPTION_GX_MAPPING.md`: bảng hợp đồng 1:1 giữa 6 corruption ↔ 4 GX expectations cho Dũng.
  - Báo cáo cá nhân `report/2A202602407_DangVanThaiAnh.md`.
- **Điều học được / Đóng góp chính:**
  - **Silent Failure**: dữ liệu bẩn không crash pipeline nhưng làm giảm `retrieval_hit_rate` từ 1.0 → 0.6.
  - **Repair Idempotency**: rebuild từ raw snapshot (deterministic) thay vì "sửa vá" corrupted (stateful, không tái lập).
  - **Reproducibility**: fixed `random.Random(42)` + reset seed mỗi lần gọi → 2 lần chạy cho cùng output.

---

## # Quy tắc ownership & review chéo (theo PHAN_CONG_NHOM.md)

| Module | Owner | Reviewer |
|---|---|---|
| `core/`, `pipelines/`, `retrieval/index.py` | Vinh | Dũng |
| `ingestion/crossref.py` | Giang | Đạt |
| `ingestion/cleaning.py`, `evaluation/testset.py` | Đạt | Giang |
| `observability/quality.py`, `observability/reporting.py` | Dũng | Vinh |
| `ingestion/corruption.py` + repair design | Thái | Đạt |
