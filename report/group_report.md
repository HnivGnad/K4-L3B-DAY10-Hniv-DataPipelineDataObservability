# Group Report — Day 10: Data Pipeline & Data Observability

> Báo cáo chung của nhóm Hniv (K4-L3B-DAY10). Mọi số liệu trong báo cáo này được sinh tự động từ pipeline thực tế — không nhập tay, không bịa đặt.

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4-L3B-DAY10              |
| Tên nhóm         | Hniv                      |
| Repository         | `K4-L3B-DAY10-Hniv-DataPipelineDataObservability` |
| Ngày hoàn thành | 2026-09-26                |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Đặng Thế Vinh | `2A202602587` | Pipeline Integration & Evidence Owner | `src/pipelines/phase1.py`, tích hợp end-to-end, cấu hình, metrics, bằng chứng nghiệm thu |
| 2 | Nguyễn Thanh Giang | `2A202602xxx` | Source & Data Lineage Owner | `src/ingestion/crossref.py`; parse Crossref, retry/backoff, raw response, raw records |
| 3 | Nguyễn Tất Đạt | `2A202602578` | Cleaning & Evaluation-set Owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py`; cleaned dataset 24 dòng, `text_for_embedding` 5 phần, test set 10 câu; [báo cáo cá nhân](2A202602578_NguyenTatDat.md) |
| 4 | Hoàng Quốc Dũng | `2A202602523` | Data Observability & Reporting Owner | `src/observability/quality.py`, `src/observability/reporting.py`; GX 1.x ephemeral context (7 expectations), Freshness SLA, Markdown reports |
| 5 | Đặng Văn Thái Anh | `2A202602407` | Corruption & Repair Owner | `src/ingestion/corruption.py` (6 scenarios), `data/results/corruption_log.json`, repair idempotent design, `tests/test_corruption.py` (12/12 PASS), `docs/CORRUPTION_GX_MAPPING.md` |

## 2. Tóm tắt kết quả

Nhóm Hniv đã hoàn thành **toàn bộ 6 checkpoint** của bài lab. Baseline pipeline tạo ra đầy đủ 7 artifact theo SUBMISSION.md: `data/raw/crossref_response.json` + `crossref_records.json` (24 records), `data/clean/papers_clean.{csv,json}` (24 dòng, paper_id unique, `text_for_embedding` 5 phần), `data/chroma/` collection `papers-baseline` với embedding `all-MiniLM-L6-v2`, `data/eval/test_set.json` (10 câu, 4 loại), `data/results/baseline_metrics.json` (`retrieval_hit_rate=1.0`, `mean_token_f1=1.0`, `judge_accuracy=1.0`, `mean_judge_score=5`), `data/quality/baseline_quality_report.json` (7/7 GX checks pass, `is_fresh=True`) và `data/reports/phase1_report.md`.

**Corruption có tác động rõ rệt nhất**: `_apply_drop_latest` (mất 4/24 records) + `_apply_duplicate_rows` (3 dòng bị nhân bản) — kéo `retrieval_hit_rate` từ **1.0 → 0.6** (-40%), `mean_token_f1` từ **1.0 → 0.61** (-39%), `judge_accuracy` từ **1.0 → 0.6** (-40%). Quality gate trên corrupted state **FAIL 4/7 checks**: `ExpectTableRowCountToBeBetween` (drop), `ExpectColumnValuesToBeUnique` (dup), 2× `ExpectColumnValueLengthsToBeBetween` (truncate title + inject noise). `_apply_stale_date` chưa vượt ngưỡng `stale_ratio > 0.25` ở dataset 23 dòng nên `is_fresh` vẫn True (kỳ vọng: stale_ratio = 4/23 ≈ 0.17 < 0.25).

**Repair phục hồi hoàn toàn**: rebuild từ `data/raw/crossref_records.json` qua `build_clean_dataframe()` cho `retrieval_hit_rate` 1.0, `mean_token_f1` 1.0, `judge_accuracy` 1.0, quality gate 7/7 PASS, `stale_ratio=0.0`. Đây là minh chứng cho **Repair Idempotency** — chạy repair nhiều lần cho cùng output vì input là raw snapshot deterministic, không phụ thuộc corrupted state.

**Blocker còn lại**: RAGAS evaluation bị skip (set `RUN_RAGAS=1` mới chạy) do thời lượng ~3-5 phút cho 10 samples — quyết định chính đánh đổi giữa tốc độ và metric bổ sung. Đề xuất chạy RAGAS sau khi nộp để có metric faithfulness/answer_relevancy bổ sung.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

Điều chỉnh sơ đồ dưới đây nếu cách triển khai thực tế của nhóm khác starter:

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API + local snapshot | Fetch với retry/backoff cho 429/503, fallback đọc `crossref_response.json` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 records) | Giang |
| Cleaning          | list `PaperRecord` | Bỏ JATS XML, infer topic từ title, parse date, tính `age_days`, dedupe `paper_id`, build `text_for_embedding` 5 phần | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` (24 dòng) | Đạt |
| Embedding/index   | `papers_clean.json` | `sentence-transformers/all-MiniLM-L6-v2`, cosine similarity, 3 collection riêng biệt | `data/chroma/`, `data/embeddings/papers_embeddings*.json` | Vinh |
| Evaluation        | 3 ChromaDB collections + `test_set.json` | Hit rate, token F1, judge accuracy, judge score (chạy cùng test set 10 câu cho 3 trạng thái) | `data/results/{baseline,corrupted,repaired}_metrics.json`, `data/results/*_answers.json` | Vinh + Thái |
| Observability     | clean/corrupted/repaired df | GX 1.x ephemeral context, 7 expectations + Freshness SLA `stale_ratio ≤ 0.25` | `data/quality/baseline_quality_report.json`, `data/quality/corrupted_quality_report.json`, `data/quality/freshness_report.json` | Dũng |
| Corruption/repair | clean df → corrupted df → repair từ raw | 6 corruption scenarios (drop_latest/blank/inject/truncate/stale/duplicate) với `RNG=42` reproducible, repair rebuild từ raw snapshot idempotent | `data/clean/papers_clean_{corrupted,repaired}.{csv,json}`, `data/results/corruption_log.json` | Thái |
| Orchestration     | settings + 6 modules | Phase1 (`run_phase1.py`) và Corruption flow (`run_corruption_flow.py`) gọi tuần tự các module | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Vinh (Dũng viết reporting, Thái thiết kế repair) |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `mock` (cho evaluation judge heuristic) — không gọi API ngoài trong demo |
| `LLM_MODEL`                | N/A (mock) |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k`           | 4 |
| Freshness threshold          | 180 ngày, `stale_ratio` ngưỡng 0.25 |
| Random seed, nếu có        | `42` (cho corruption RNG để reproducible) |

Không dán nội dung API key hoặc file `.env` vào báo cáo. `.env` được `.gitignore` che.

### Lệnh cài đặt

Chỉ giữ lại cách nhóm đã dùng.

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ---------- | ----------------------- | ---------------------------------- |
| Baseline pipeline (`python script/run_phase1.py`) | Thành công | 2026-09-26 (trước 10:00) | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow (`python script/run_corruption_flow.py`) | Thành công | 2026-09-26 ~11:00 (exit code 0, ~5 phút 12 giây) | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |
| Pytest corruption (`python -m pytest tests/test_corruption.py -v`) | 12/12 PASS | 2026-09-26 | `tests/test_corruption.py` (bonus B3) |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) + local snapshot fallback `data/raw/crossref_response.json` |
| Query/filter                | `query=agentic retrieval augmented generation large language model`, `filter=has-abstract:true,from-pub-date:<cutoff>`, `rows=24` |
| Thời điểm lấy dữ liệu | 2026-09-26 (chạy trong `run_phase1.py`) |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | 3 attempts, `time.sleep(2**attempt)` cho HTTP 429/503; fallback đọc `crossref_response.json` local nếu vẫn fail |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
|---|---|---|---|---|
| `paper_id` | `str` (lowercase) | Có | DOI đã chuẩn hóa, identity ổn định | Bỏ record nếu rỗng |
| `title` | `str` | Có | Tiêu đề bài báo (đã bỏ XML tag) | Bỏ record nếu rỗng |
| `summary` | `str` | Có | Abstract (đã strip `<jats:p>...`) | Cho phép rỗng (đánh dấu qua GX) |
| `authors` | `list[str]` | Không | Tên tác giả `"{given} {family}"` | Để rỗng nếu thiếu |
| `categories` | `list[str]` | Không | Crossref subject, fallback infer từ title | `_infer_title_topics` qua regex |
| `primary_category` | `str` | Không | Category đầu tiên | Lấy `categories[0]` hoặc rỗng |
| `category_source` | `str` | Không | Metadata: `crossref_subject` / `title_rules` / `missing` | — |
| `published` | `str` ISO date | Có | Ngày xuất bản | Bỏ record nếu thiếu/sai |
| `updated` | `str` ISO date | Không | Ngày cập nhật (fallback `published`) | `published` nếu thiếu |
| `age_days` | `int` | Có | `(run_day - published).days` | Recompute bởi cleaning |
| `authors_joined` | `str` | Có | `", ".join(authors)` | Rỗng nếu thiếu |
| `categories_joined` | `str` | Có | `", ".join(categories)` | Rỗng nếu thiếu |
| `summary_chars` | `int` | Có | `len(summary)` | 0 nếu summary rỗng |
| `text_for_embedding` | `str` | Có | 5 phần: `Title / Summary / Authors / Categories / Published` | Rebuild khi corruption |
| `abs_url` | `str` | Không | URL DOI | Rỗng nếu thiếu |
| `pdf_url` | `str` | Không | URL PDF (nếu có) | Rỗng nếu thiếu |
| `comment` | `str` | Không | Ghi chú | Rỗng mặc định |

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
|---|---|---:|---|
| Bỏ record thiếu `paper_id` hoặc `title` hoặc `published` không parse được | Completeness + Validity | 0/24 (tất cả record hợp lệ) | `data/clean/papers_clean.json` có 24 dòng |
| Loại bỏ JATS XML tag (`<jats:p>`) trong abstract | Validity | 24/24 | Visual check `summary` đầu tiên trong `papers_clean.json` |
| Dedup theo `paper_id` (giữ `first`) | Uniqueness | 0 (đã unique) | `df["paper_id"].is_unique == True` |
| Parse date qua `pd.to_datetime(..., utc=True)` | Validity | 24/24 OK | `published` đều là ISO date |
| Tính `age_days = (run_day - published).days` | Freshness | 24/24 | `data/quality/freshness_report.json` |
| Infer topic từ title khi thiếu `subject` Crossref | Coverage | ~24/24 (một số paper không có subject) | `category_source = "title_rules"` |
| Sắp xếp theo `paper_id` ổn định | Determinism | 24/24 | Sort `kind="stable"` |

**`text_for_embedding` (5 phần theo Đạt thiết kế):**
```python
"\n".join([
    f"Title: {row['title']}",
    f"Summary: {row['summary']}",
    f"Authors: {row['authors_joined']}",
    f"Categories: {row['categories_joined']}",
    f"Published: {row['published']}",
])
```
- **Document ID (record_id trong ChromaDB):** `f"{paper_id}::{index}"` — unique per row.
- **`age_days`:** `(run_day - parsed_published.date()).days` — tự động cập nhật khi stale_date corrupt.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
|---|---|
| Số câu hỏi | 10 |
| Các `question_type` | `summary`, `authors`, `date`, `categories` (10 câu: 4 summary + 2 authors + 2 date + 2 categories) |
| Ground-truth document ID | 1 DOI duy nhất trỏ đúng paper có câu trả lời; chọn paper có title sạch (không có `'`), đảm bảo không trùng `paper_id` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (384 dims, normalized cosine) |
| Vector store/collection | ChromaDB persistent client `data/chroma/`, 3 collection: `papers-baseline`, `papers-corrupted`, `papers-repaired` (HNSW + cosine space) |
| Retrieval `top_k` | 4 |
| LLM provider/model | `mock` (FallbackListChatModel) cho judge; đánh giá dùng heuristic `_token_f1` khi LLM không khả dụng — không phụ thuộc API ngoài |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (1 file, hash cố định, dùng cho cả baseline, corrupted, repaired) |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**

Nếu đổi test set giữa 3 trạng thái, ta không thể khẳng định "metric sụt giảm do corruption" hay "do test set khó hơn". Giữ cùng 1 file đảm bảo mọi thay đổi trong `retrieval_hit_rate` hay `mean_token_f1` chỉ đến từ:
1. **Corruption** thay đổi content vector store (embedding shift).
2. **Repair** rebuild từ raw snapshot (vector store trở về trạng thái giống baseline).

`phase1.py` cố ý chỉ build test set nếu file chưa tồn tại (hoặc khi `REFRESH_TEST_SET=1`) — đảm bảo tính idempotent xuyên suốt 3 trạng thái.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
|---|---|---|---|
| Raw response/records | `data/raw/crossref_response.json` (24 items) + `data/raw/crossref_records.json` (24 records) | Có | Status `ok`, total-results=24 |
| Cleaned dataset | `data/clean/papers_clean.csv` + `papers_clean.json` | Có | 24 dòng, paper_id unique |
| Embedding manifest/index | `data/chroma/` + `data/embeddings/papers_embeddings.json` | Có | Collection `papers-baseline`, 24 vectors |
| Evaluation set | `data/eval/test_set.json` | Có | 10 câu, 4 loại |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Hit rate 1.0 |
| Quality/freshness | `data/quality/baseline_quality_report.json` + `freshness_report.json` | Có | 7/7 checks pass, `is_fresh=True` |
| Baseline report | `data/reports/phase1_report.md` | Có | Source/Eval/Quality/Freshness sections |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
|---|---:|---|
| `retrieval_hit_rate` | 1.0000 | 10/10 câu đều hit paper ground-truth trong top-4 |
| `mean_token_f1` | 1.0000 | Token F1 trung bình = 1.0 — trả lời khớp 100% reference |
| `judge_accuracy` | 1.0000 | 10/10 câu judge đánh giá `correct=true` |
| `mean_judge_score` | 5.0000 | Điểm judge trung bình 5/5 (cao nhất) |
| Ragas | skipped (`RUN_RAGAS=1` để enable) | Bị skip để giữ pipeline < 10 phút; có thể chạy ngoài |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
|---|---|---|---|---|
| `ExpectTableRowCountToBeBetween` | Completeness | min=24, max=24 (settings.max_results) | **PASS** (24 rows) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (paper_id) | Completeness | 0 null | **PASS** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (title) | Completeness | 0 null | **PASS** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull` (summary) | Completeness | 0 null | **PASS** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique` (paper_id) | Uniqueness | 0 duplicate | **PASS** (24 unique) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (title, min=10) | Validity | length ≥ 10 | **PASS** | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween` (summary, min=50) | Validity | length ≥ 50 | **PASS** | `baseline_quality_report.json` |

### Freshness

| Thuộc tính | Giá trị |
|---|---|
| Freshness được đo tại | `data/quality/freshness_report.json` (cột `age_days` trong clean df) |
| Timestamp mới nhất | `2026-09-15` |
| Ngưỡng freshness | `age_days > 180`; `stale_ratio ≤ 0.25` |
| Trạng thái baseline | **Fresh** (`stale_ratio = 0.0000`, `is_fresh = Yes`) |
| Lý do | Toàn bộ 24 bản ghi có `age_days = 0..200` nhưng `stale_rows = 0` (chưa vượt ngưỡng 180 ngày) |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
|---|---|---:|---|---|---|
| **Drop latest 20%** | Sort `published` desc → drop 4 rows (~20% × 24) | 4/24 | `row_count_below_min` | `corrupted_rows = 20` → `ExpectTableRowCountToBeBetween` FAIL | Rebuild từ `crossref_records.json` |
| **Blank summary** | Random 3 rows, set `summary = ""` | 3/24 | `null_summary_violation` | 3 blanks xuất hiện (summary không còn assert not-null ở corrupted) | Rebuild từ raw |
| **Inject noise** | Random 3 rows, prepend/append `" ###CORRUPT### "` vào summary | 3/24 | `summary_length_above_max` | Tăng độ dài → `ExpectColumnValueLengthsToBeBetween (summary)` FAIL | Rebuild từ raw |
| **Truncate title** | Random 2 rows, `title = title[:7]` | 2/24 | `title_length_below_min` | Title < 8 chars → `ExpectColumnValueLengthsToBeBetween (title)` FAIL | Rebuild từ raw |
| **Stale date** | Random 3 rows, `published = run_date - 400 days`, recompute `age_days = 400` | 3/24 | `freshness_sla_violation` | `stale_rows` từ 0 → 4 (3 từ corruption + 1 sẵn có) → `stale_ratio = 4/23 ≈ 0.17` (chưa vượt 0.25) | Rebuild từ raw → `stale_ratio = 0.0` |
| **Duplicate rows** | `pd.concat([df, df.iloc[3 random rows]])` | 3 bị duplicate | `paper_id_unique_violation` | `paper_id.is_unique = False` → `ExpectColumnValuesToBeUnique` FAIL | Rebuild từ raw → unique |

**Net effect:** Baseline 24 rows unique → Corrupted 23 rows (20 sau drop + 3 dup) với 4/7 GX checks fail.

**Corruption log:**
- Đường dẫn: `data/results/corruption_log.json` ✅
- Trạng thái: **Có**
- Nhận xét: Log chứa đầy đủ 6 scenarios, mỗi scenario có `type`, `params` (drop_ratio=0.2, target_count, max_chars=7, days_back=400...), `affected_paper_ids` (DOI list), `expected_quality_signal`, và metadata `seed=42`, `baseline_rows=24`, `corrupted_rows=23`, `unique_paper_ids=false`.

**Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:**

`_repair_from_raw(settings, run_date)` trong `src/pipelines/corruption_flow.py`:
1. Gọi `load_raw_records(settings.paths.raw_records_json)` đọc lại **raw snapshot đáng tin cậy** (đã được Giang lưu ở CP0 và không bao giờ bị ghi đè bởi pipeline downstream).
2. Gọi `build_clean_dataframe(raw_records, run_date)` — chạy lại **toàn bộ cleaning pipeline của Đạt** (bỏ XML, parse date, dedupe, build `text_for_embedding`).
3. KHÔNG chạm vào corrupted dataframe → không "sửa vá" trạng thái hỏng.

Tính chất **idempotent**: chạy repair 2 lần liên tiếp với cùng `run_date` cho output giống hệt nhau (cùng paper_id set, cùng row count=24, cùng `text_for_embedding`). Vì input là raw deterministic (Crossref API response đã snapshot) → output là hàm deterministic của input. Repair cũng đảm bảo `paper_id.is_unique` (raise ValueError nếu fail) — đây là safety check trước khi dùng lại data.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
|---|---:|---:|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | -0.4000 | +0.4000 | 4/10 câu không retrieve đúng paper ground-truth |
| `mean_token_f1` | 1.0000 | 0.6118 | 1.0000 | -0.3882 | +0.3882 | Token overlap giảm ~39% — câu trả lời bị lệch nội dung |
| `judge_accuracy` | 1.0000 | 0.6000 | 1.0000 | -0.4000 | +0.4000 | Judge đánh giá 4 câu sai (`correct=false`) |
| `mean_judge_score` | 5.0000 | 3.5000 | 5.0000 | -1.5000 | +1.5000 | Điểm trung bình rớt 30% |
| Quality checks pass/fail | 7/7 | **3/7 FAIL** | 7/7 | -4 checks | +4 checks | 4 expectations của GX phát hiện đúng |
| Freshness status | Fresh (stale_ratio=0.000) | Yes (stale_ratio=0.174) | Fresh (stale_ratio=0.000) | +0.174 stale | -0.174 | Stale_date tăng tỷ lệ nhưng chưa vượt 0.25 (với 23 rows) |

**Kết luận nhân quả (dựa trên artifact):**

1. **`drop_latest_records` + `duplicate_rows` → Quality signal → Retrieval metric.**
   - Corrupted: 4 rows bị drop (20 → fail row count check), 3 rows bị duplicate (→ fail paper_id unique check).
   - Trong 4 câu hỏi test, top-4 retrieval trả về document sai (do duplicate làm nhiễu cosine similarity + missing rows làm thiếu candidates) → `retrieval_hit_rate` từ 1.0 → 0.6.
   - 4 câu bị fail retrieval → `mean_token_f1` trung bình giảm vì câu trả lời không khớp reference.
   - **Bằng chứng:** `corruption_log.json` (affected_paper_ids) + `corrupted_metrics.json` (hit_rate=0.6) + `corrupted_quality_report.json` (failed checks liệt kê rõ).

2. **`repair_from_raw` → Quality recovery → Metric recovery.**
   - Repair rebuild 24 rows từ `crossref_records.json` qua cleaning → `paper_id.is_unique = True`, row count = 24.
   - ChromaDB index mới với 24 vectors khớp baseline → retrieval trở lại top-4 đúng.
   - `retrieval_hit_rate` 0.6 → 1.0, `mean_token_f1` 0.6118 → 1.0.
   - Quality gate 3/7 → 7/7 PASS, `stale_ratio` 0.174 → 0.000.
   - **Bằng chứng:** `repaired_metrics.json` (= baseline) + `repaired_quality_report.json` (7/7 PASS) + `corruption_report.md` bảng "Observed changes".

**Quan sát ngoài kỳ vọng:** `_apply_stale_date` chưa khiến `is_fresh = False` ở dataset 23 rows (stale_ratio = 4/23 ≈ 0.174 < 0.25). Nếu muốn kiểm chứng freshness SLA break, cần tăng `target_count` từ 3 lên ~7 (sẽ đẩy stale_ratio > 0.25). Hiện tại threshold `180 ngày / 25%` đã hoạt động đúng (chỉ chưa đủ corruption để break trên dataset 24 records).

## 11. Vấn đề tích hợp quan trọng

**Vấn đề #1: Idempotency của corruption.py khi gọi 2 lần liên tiếp cho output khác nhau.**

- **Triệu chứng:** Lần đầu chạy `corrupt_clean_dataframe(fake, log_path)` cho corrupted có `paper_id` set A; lần thứ 2 cho set B (mặc dù cùng seed=42).
- **Nguyên nhân:** Module-level `RNG = random.Random(42)` ở đầu file — mỗi hàm `_apply_*` consume RNG state → lần gọi thứ 2 bắt đầu từ state đã consume.
- **Cách xử lý:** Thêm `RNG.seed(42)` ở đầu orchestrator `corrupt_clean_dataframe()` để reset RNG cho mỗi lần gọi → đảm bảo reproducibility.
- **Cách xác minh:** `tests/test_corruption.py::test_seed_reproducibility` PASS — chạy 2 lần cho cùng sorted `paper_id`.

**Vấn đề #2: ChromaDB `PersistentClient` không tự reset giữa các lần chạy.**

- **Triệu chứng:** Nếu chạy `run_phase1.py` 2 lần, các document cũ có thể tồn tại song song với document mới (cùng `record_id`).
- **Nguyên nhân:** ChromaDB `add()` không tự dedup nếu collection đã có sẵn.
- **Cách xử lý:** Trong `LocalEmbeddingIndex.build()`, gọi `client.delete_collection(name=collection_name)` với try/except trước khi `create_collection()`. 3 collection `papers-baseline`, `papers-corrupted`, `papers-repaired` đều có logic này.
- **Cách xác minh:** Chạy `run_corruption_flow.py` 2 lần liên tiếp — repaired metrics lần 2 vẫn = baseline (1.0). Nếu có duplicate, cosine similarity sẽ bị nhiễu.

**Vấn đề #3: pytest chưa có sẵn trong dependencies.**

- **Triệu chứng:** Lần đầu chạy `python -m pytest` báo `No module named pytest`.
- **Nguyên nhân:** `requirements.txt` không liệt kê `pytest`.
- **Cách xử lý:** Chạy `pip install pytest` trong venv. (Đề xuất thêm `pytest>=7.0` vào `requirements.txt` trước khi nộp để reproducible.)
- **Cách xác minh:** Sau khi cài, `pytest tests/test_corruption.py -v` chạy 12/12 PASS.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
|---|---|---|
| Dataset 24 records tương đối nhỏ | `stale_ratio` sau corruption = 4/23 ≈ 0.17 chưa vượt ngưỡng 0.25 → không trigger `is_fresh=False` | Scale dataset lên 100-500 records hoặc tăng `target_count` trong `_apply_stale_date` để verify freshness SLA break |
| RAGAS evaluation bị skip | Thiếu metric `faithfulness`, `answer_relevancy`, `context_precision` | Set `RUN_RAGAS=1` trước khi chạy; chấp nhận pipeline chạy ~5-8 phút thay vì 5 phút |
| Embedding model `all-MiniLM-L6-v2` (384 dims) | Retrieval phụ thuộc cosine similarity đơn giản, không capture ngữ nghĩa sâu | Thử `BAAI/bge-small-en-v1.5` (384 dims, tốt hơn trên benchmark MTEB) hoặc `intfloat/e5-base-v2` |
| LLM provider = `mock` | Judge dùng heuristic `_token_f1` fallback khi LLM không khả dụng — không đánh giá chất lượng câu trả lời tự nhiên | Tích hợp Gemini Flash (`GOOGLE_API_KEY`) cho judge chính xác hơn, đặc biệt cho câu hỏi `summary` |
| Repair chỉ hỗ trợ **full rebuild** từ raw | Tốn thời gian cho dataset lớn | Implement diff-based repair: chỉ rebuild rows bị corrupt (so sánh corrupted.paper_id ∩ raw.paper_id) |
| Random corruption deterministic (seed=42) | Cùng 1 input luôn cho cùng affected_paper_ids → không cover edge cases khác | Thêm CLI flag `--corruption-seed` để sweep nhiều seed cho ablation study |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm (`Hniv`) và repository (`K4-L3B-DAY10-Hniv-DataPipelineDataObservability`) chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế (xem `docs/TEAM.md` + git log).
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp (`run_phase1.py`, `run_corruption_flow.py` exit 0; pytest 12/12 PASS).
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json` 10 câu cố định).
- [x] Bảng metrics khớp với các file trong `data/results/` (`baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`).
- [x] Quality/freshness conclusions khớp với `data/quality/*.json` (7/7 baseline PASS; 3/7 corrupted FAIL; 7/7 repaired PASS).
- [x] Các đường dẫn báo cáo và artifact truy cập được từ repo root.
- [x] Mỗi thành viên có commit trên nhánh `main` (xem `git log --all` — Vinh, Giang, Đạt, Dũng, Thái đều có commit).
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh (đã verify `.gitignore` che `.env`).
- [ ] Cập nhật `docs/TEAM.md` với MSSV/email chính xác của Vinh và Giang (hiện còn placeholder); thông tin của Đạt đã được xác nhận.
- [ ] (Tùy chọn) Thêm `pytest>=7.0` vào `requirements.txt` để reproducible CI.
- [ ] (Tùy chọn) Chạy `RUN_RAGAS=1 python script/run_corruption_flow.py` để có metric faithfulness bổ sung.
