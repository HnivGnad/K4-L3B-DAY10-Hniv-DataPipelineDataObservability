# Kế hoạch phân công nhóm — Data Pipeline & Data Observability

> **Nhóm:** `[Bổ sung tên nhóm]`  
> **Lớp:** `K4-L3B-DAY10`  
> **Thời lượng:** 240 phút  
> **Thành viên:** Vinh, Giang, Đạt, Dũng, Thái  
> **Trạng thái tài liệu:** Kế hoạch thực hiện; chỉ đánh dấu hoàn thành khi có code, artifact và kết quả chạy thực tế.

## 1. Mục tiêu chung

Nhóm cần hoàn thiện pipeline theo luồng:

```text
Crossref API/local snapshot
    → raw response và raw records
    → cleaned dataset
    → embedding và ChromaDB index
    → evaluation baseline
    → quality gate và freshness SLA
    → corrupted dataset
    → evaluation sau corruption
    → repair từ raw records
    → so sánh Baseline / Corrupted / Repaired
```

Các yêu cầu bắt buộc:

- Hoàn thiện toàn bộ `TODO(student)` và `NotImplementedError` trong `src/`.
- Chạy thành công `script/run_phase1.py` và `script/run_corruption_flow.py`.
- Great Expectations phải dùng API phiên bản 1.x và có đủ bốn expectations thiết yếu.
- Freshness SLA dùng `age_days`, ngưỡng stale là trên 180 ngày; dataset không fresh khi tỷ lệ stale vượt 25%.
- Corruption flow phải có đủ sáu kịch bản lỗi và dùng cùng một test set cho ba trạng thái.
- Báo cáo và số liệu phải được sinh từ pipeline thực tế, không sửa tay hoặc tự tạo số liệu.
- Tất cả thành viên có commit trên nhánh `main`, có báo cáo cá nhân và tự nộp link repo lên VLearn.

## 2. Phân công tổng quan

| Thành viên | Vai trò chính | Phạm vi sở hữu | Người review chéo | Bàn giao chính |
|---|---|---|---|---|
| **Vinh** | Pipeline Integration & Evidence Owner | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, cấu hình, tích hợp, chạy end-to-end, kiểm tra artifact và hồ sơ nộp bài | Dũng | Hai flow chạy được, metrics ba trạng thái, bằng chứng tái hiện, checklist nộp bài |
| **Giang** | Source & Data Lineage Owner | `src/ingestion/crossref.py`, raw schema, API retry/fallback, lưu raw artifacts | Đạt | `crossref_response.json`, `crossref_records.json`, 24 `PaperRecord` hợp lệ |
| **Đạt** | Cleaning & Evaluation-set Owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py`, clean schema và test-set contract | Giang | Clean CSV/JSON 24 dòng, `text_for_embedding`, test set 10 câu |
| **Dũng** | Data Observability & Reporting Owner | `src/observability/quality.py`, `src/observability/reporting.py`, GX 1.x, freshness, báo cáo Markdown | Vinh | Quality/freshness JSON, `phase1_report.md`, `corruption_report.md` |
| **Thái** | Corruption & Repair Owner | `src/ingestion/corruption.py`, thiết kế sáu lỗi, corruption log, kiểm chứng dữ liệu repair | Đạt | Corrupted dataset, log đủ sáu lỗi, quy tắc repair idempotent và kết quả kiểm chứng |

Nguyên tắc ownership: owner trực tiếp viết và giải thích phần được giao; reviewer chạy lại, kiểm tra contract và ghi nhận lỗi. Vinh điều phối tích hợp nhưng không nhận thay ownership kỹ thuật của các thành viên khác.

## 3. Công việc chi tiết từng thành viên

### 3.1. Vinh — Nhóm trưởng, Pipeline Integration & Evidence Owner

#### Đầu việc chính

1. Chốt contract dùng chung trước khi nhóm code:
   - schema `PaperRecord`;
   - danh sách cột của clean dataframe;
   - định dạng test set;
   - quy tắc giữ ổn định `paper_id`;
   - tên collection và đường dẫn artifact trong `src/core/config.py`;
   - một test set duy nhất cho baseline, corrupted và repaired.
2. Rà soát `src/core/config.py`, `src/core/utils.py`, `.env.example`, `pyproject.toml` và `requirements.txt`:
   - không hard-code đường dẫn máy cá nhân;
   - không đưa secret vào repo;
   - thống nhất provider/model dùng khi demo;
   - bảo đảm import chạy từ hai entrypoint.
3. Hoàn thiện `src/pipelines/phase1.py`:
   - load/fetch raw records;
   - clean và lưu CSV/JSON;
   - build collection `papers-baseline`;
   - tạo hoặc dùng lại test set;
   - evaluate và ghi baseline metrics/answers;
   - chạy quality/freshness;
   - gọi hàm tạo `phase1_report.md`.
4. Hoàn thiện `src/pipelines/corruption_flow.py`:
   - đọc baseline và cleaned dataset;
   - tạo/index/evaluate corrupted state;
   - chạy quality/freshness cho corrupted state;
   - repair lại từ raw records, không sửa trực tiếp bản corrupted;
   - tạo/index/evaluate repaired state;
   - gọi báo cáo so sánh ba trạng thái.
5. Chạy tích hợp sau mỗi checkpoint, ghi lỗi theo module và trả lại đúng owner xử lý.
6. Đối chiếu metrics trong JSON với bảng trong báo cáo; không chấp nhận số liệu nhập tay.
7. Điều phối live demo và checklist nộp bài; xác nhận mỗi thành viên có commit và báo cáo cá nhân.

#### Input phụ thuộc

- Raw records từ Giang.
- Clean dataframe và test set từ Đạt.
- Quality/reporting functions từ Dũng.
- Corruption function và quy tắc repair từ Thái.

#### Output bàn giao

- `data/results/baseline_metrics.json`
- `data/results/corrupted_metrics.json`
- `data/results/repaired_metrics.json`
- Các file answers tương ứng trong `data/results/`
- Pipeline end-to-end chạy được từ hai entrypoint.
- Bằng chứng lệnh chạy và checklist nghiệm thu cuối.

#### Tiêu chí hoàn thành

- Hai lệnh chính đều exit code 0.
- Cùng một `data/eval/test_set.json` được dùng cho cả ba trạng thái.
- Có ba ChromaDB collection tách biệt: `papers-baseline`, `papers-corrupted`, `papers-repaired`.
- Tất cả artifact đúng đường dẫn trong `Settings.paths`.
- Report đọc số liệu từ artifact thực tế và khớp với các file metrics.

### 3.2. Giang — Source & Data Lineage Owner

#### Đầu việc chính

1. Hoàn thiện `parse_crossref_payload()` trong `src/ingestion/crossref.py`:
   - duyệt `payload["message"]["items"]`;
   - lấy DOI làm `paper_id` ổn định;
   - parse title, abstract, authors, subject/categories, dates và URLs;
   - xử lý trường thiếu an toàn;
   - loại record không đủ định danh hoặc tiêu đề.
2. Hoàn thiện `fetch_source_records()`:
   - gọi Crossref theo cấu hình;
   - retry/backoff cho lỗi tạm thời như 429/503;
   - có timeout và fallback về local snapshot khi API lỗi/mất mạng;
   - bảo toàn raw API response;
   - serialize parsed records ra JSON.
3. Hoàn thiện `load_raw_records()` để ánh xạ JSON snapshot về `PaperRecord`.
4. Viết mô tả raw schema và quy tắc field thiếu để Đạt dùng nhất quán.
5. Xác minh đủ 24 records, `paper_id` không rỗng và raw snapshot không bị chỉnh sửa bởi các bước sau.

#### Output bàn giao

- `data/raw/crossref_response.json`
- `data/raw/crossref_records.json`
- Danh sách 24 `PaperRecord` có schema thống nhất.
- Ghi chú data lineage: nguồn, thời điểm lấy, fallback đã dùng hay không.

#### Tiêu chí hoàn thành

```bash
python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(len(r))"
```

- Kết quả mong đợi: `24`.
- Chạy được khi có mạng và vẫn chạy được từ snapshot khi nguồn sống không khả dụng.
- Không ghi API key/token vào raw response, log hoặc source code.

### 3.3. Đạt — Cleaning & Evaluation-set Owner

#### Đầu việc chính

1. Hoàn thiện `build_clean_dataframe()` trong `src/ingestion/cleaning.py`:
   - loại JATS/XML tag trong abstract;
   - chuẩn hóa khoảng trắng và kiểu dữ liệu;
   - parse `published`, `updated`;
   - tính `age_days = (run_date - published).days`;
   - tạo `authors_joined`, `categories_joined`, `summary_chars`;
   - tạo `text_for_embedding` đủ năm phần theo contract của bài;
   - deduplicate theo `paper_id`;
   - loại dòng lỗi và sắp xếp kết quả ổn định.
2. Chốt clean schema với Giang và Thái để corruption có thể rebuild `text_for_embedding` đúng cách.
3. Hoàn thiện `build_test_set()` trong `src/evaluation/testset.py`:
   - tạo đúng 10 câu hỏi;
   - phủ đủ `summary`, `authors`, `date`, `categories`;
   - mỗi câu có `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`;
   - ground truth lấy từ clean dataframe, không nhập dữ liệu không có trong corpus;
   - kết quả có thứ tự ổn định để tái hiện.
4. Kiểm tra test set vẫn hợp lệ khi chạy corruption và repair; không tạo lại test set giữa ba trạng thái.

#### Output bàn giao

- `data/clean/papers_clean.csv`
- `data/clean/papers_clean.json`
- `data/eval/test_set.json`
- Mô tả clean schema và cấu trúc `text_for_embedding`.

#### Tiêu chí hoàn thành

```bash
python -c "from datetime import datetime, timezone; from core.config import load_settings; from ingestion.crossref import load_raw_records; from ingestion.cleaning import build_clean_dataframe; s=load_settings(); df=build_clean_dataframe(load_raw_records(s.paths.raw_records_json), datetime.now(timezone.utc)); print(len(df), df['paper_id'].is_unique)"
```

- Kết quả mong đợi: `24 True`.
- Không có `paper_id`, `title` hoặc `text_for_embedding` rỗng.
- Test set có đúng 10 câu và đủ bốn `question_type`.

### 3.4. Dũng — Data Observability & Reporting Owner

#### Đầu việc chính

1. Hoàn thiện `run_data_quality_checks()` trong `src/observability/quality.py` bằng Great Expectations 1.x:
   - dùng ephemeral context và Pandas data source/asset/batch definition;
   - `ExpectTableRowCountToBeBetween`;
   - `ExpectColumnValuesToNotBeNull`;
   - `ExpectColumnValuesToBeUnique`;
   - `ExpectColumnValueLengthsToBeBetween`;
   - tổng hợp kết quả dễ đọc và ghi JSON vào `data/quality/`.
2. Tích hợp freshness vào quality gate:
   - stale khi `age_days > 180`;
   - tính `stale_rows`, `total_rows`, `stale_ratio`;
   - `is_fresh = False` khi `stale_ratio > 0.25`.
3. Hoàn thiện `build_freshness_report()`:
   - latest/oldest published;
   - số dòng stale và tổng số dòng;
   - tỷ lệ stale, ngưỡng và trạng thái fresh.
4. Hoàn thiện `generate_phase1_report()` và `generate_corruption_report()`:
   - chỉ lấy dữ liệu từ payload/metrics truyền vào;
   - bảng so sánh Baseline / Corrupted / Repaired;
   - hiển thị quality/freshness signal;
   - nêu quan hệ nguyên nhân → tín hiệu → ảnh hưởng khi có số liệu hỗ trợ.
5. Review tích hợp với Vinh để bảo đảm báo cáo không che giấu check fail và không bịa số liệu.

#### Output bàn giao

- `data/quality/baseline_quality_report.json`
- `data/quality/corrupted_quality_report.json`
- Các freshness/quality artifact cần thiết cho ba trạng thái.
- `data/reports/phase1_report.md`
- `data/reports/corruption_report.md`

#### Tiêu chí hoàn thành

```bash
python -c "from core.config import load_settings; from observability.quality import run_data_quality_checks; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); r=run_data_quality_checks(df, s, 'test'); print(r['success'])"
```

- Baseline hợp lệ trả về `True`.
- Corrupted state làm ít nhất một quality/freshness signal đổi theo đúng lỗi đã tiêm.
- Great Expectations không dùng API cũ/deprecated gây crash.
- Các con số trong Markdown khớp tuyệt đối với JSON artifacts.

### 3.5. Thái — Corruption & Repair Owner

#### Đầu việc chính

1. Hoàn thiện `corrupt_clean_dataframe()` trong `src/ingestion/corruption.py` với đủ sáu kịch bản:
   - drop 20% records mới nhất;
   - blank summary;
   - inject noise vào summary/text;
   - truncate title xuống dưới 8 ký tự;
   - đẩy published date về quá khứ;
   - duplicate rows.
2. Mỗi corruption phải xác định được:
   - loại lỗi;
   - record bị tác động;
   - tham số hoặc giá trị trước/sau cần thiết;
   - quality signal dự kiến;
   - ảnh hưởng dự kiến đến retrieval/answer.
3. Rebuild tất cả cột dẫn xuất bị ảnh hưởng, đặc biệt `summary_chars`, `age_days` và `text_for_embedding`; không để dữ liệu gốc và cột dẫn xuất mâu thuẫn.
4. Ghi `data/results/corruption_log.json` có đủ sáu loại lỗi.
5. Phối hợp Vinh thiết kế repair idempotent:
   - luôn dựng repaired dataframe lại từ `data/raw/crossref_records.json` qua cleaning pipeline;
   - không sửa vá trực tiếp corrupted dataframe;
   - chạy repair nhiều lần cho kết quả tương đương;
   - so sánh schema, số dòng và `paper_id` với baseline.
6. Review test set với Đạt để các lỗi đủ khả năng tạo tác động đo được nhưng không làm pipeline crash ngoài chủ đích.

#### Output bàn giao

- `data/clean/papers_clean_corrupted.csv`
- `data/clean/papers_clean_corrupted.json`
- `data/results/corruption_log.json`
- Quy tắc repair và bằng chứng repaired data được dựng từ raw source.

#### Tiêu chí hoàn thành

- Log chứa đủ sáu corruption types và danh sách record bị tác động.
- Corrupted dataframe tạo được index để đo silent failure, không chỉ làm chương trình crash.
- Quality gate phát hiện lỗi dữ liệu tương ứng.
- Repair chạy lặp lại không tích lũy duplicate/noise và phục hồi được các contract chính.

## 4. Contract tích hợp bắt buộc

| Contract | Quy ước nhóm phải giữ |
|---|---|
| Raw identity | `paper_id` ổn định, ưu tiên DOI đã chuẩn hóa |
| Clean identity | Deduplicate theo `paper_id`; không đánh lại ID giữa các trạng thái |
| Clean schema | Các cột nguồn và cột dẫn xuất có tên/kiểu nhất quán ở baseline, corrupted, repaired |
| Embedding text | Mọi thay đổi title/summary/metadata liên quan phải rebuild `text_for_embedding` |
| Test set | Chỉ tạo một lần từ baseline; cùng file/hash dùng cho cả ba trạng thái |
| Vector collections | Tách riêng `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Artifact paths | Chỉ dùng đường dẫn từ `src/core/config.py`, không hard-code đường dẫn tuyệt đối |
| Metrics | Giữ nguyên tên metric: `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` |
| Repair source | Dựng lại từ raw snapshot đáng tin cậy qua cleaning, không phục hồi từ dữ liệu đã corrupted |
| Evidence | Mọi kết luận phải trỏ được tới code, log, JSON metric hoặc Markdown report sinh từ pipeline |

## 5. Kế hoạch phối hợp theo checkpoint 240 phút

| Thời gian | Checkpoint | Người thực hiện chính | Công việc song song | Điểm đồng bộ/bàn giao |
|---|---|---|---|---|
| 00–15 phút | Khởi động | Vinh | Cả nhóm cài môi trường, tạo nhánh làm việc, kiểm tra `.env` | Vinh chốt contract, lệnh chạy và quy ước commit |
| 15–30 phút | CP0: Raw ingestion | Giang | Vinh kiểm tra config; Đạt đọc raw schema | Bàn giao 24 raw records cho Đạt và Vinh |
| 30–65 phút | CP1: Cleaning + Observability | Đạt, Dũng | Giang review cleaning; Vinh dựng orchestration khung | Chốt clean schema 24 dòng; quality baseline chạy được |
| 65–95 phút | CP2: Test set + Index | Đạt, Vinh | Dũng kiểm tra quality artifact; Thái chuẩn bị corruption design | Bàn giao test set 10 câu và baseline collection |
| 95–120 phút | CP3: Baseline E2E | Vinh | Dũng hoàn thiện phase-1 report; các owner sửa lỗi module | Baseline metrics/report được sinh từ lệnh chính |
| 120–165 phút | CP4: Corruption | Thái | Vinh index/evaluate corrupted; Dũng chạy quality/freshness | Log đủ sáu lỗi và corrupted metrics |
| 165–210 phút | CP5: Repair + Comparison | Vinh, Thái | Dũng tạo comparison report; Đạt xác minh schema/test set | Repaired metrics và bảng ba trạng thái |
| 210–240 phút | CP6: Demo + Nghiệm thu | Vinh điều phối, cả nhóm tham gia | Mỗi người kiểm tra report cá nhân và commit | Demo, Q&A, checklist repo và LMS |

### Quy tắc báo blocker

- Blocker quá 5 phút: ghi lỗi nguyên văn đã che secret, lệnh tái hiện và owner liên quan vào kênh nhóm.
- Blocker quá 10 phút: Vinh chỉ định một reviewer ghép cặp với owner.
- Không sửa contract chung âm thầm; thay đổi schema/path phải báo cho tất cả module phụ thuộc.
- Không merge phần việc nếu chưa có lệnh hoặc artifact xác minh tối thiểu.

## 6. Ma trận kiểm tra chéo

| Hạng mục | Owner | Reviewer | Cách kiểm tra |
|---|---|---|---|
| Crossref parsing/fallback | Giang | Đạt | Đủ 24 records, schema ổn định, fallback chạy được |
| Cleaning/schema | Đạt | Giang | 24 dòng, `paper_id` unique, cột bắt buộc không rỗng |
| Evaluation set | Đạt | Thái | 10 câu, đủ bốn loại, doc ID tồn tại trong baseline |
| GX 1.x/freshness | Dũng | Vinh | Baseline pass; corrupted signal thay đổi đúng kỳ vọng |
| Corruption suite | Thái | Đạt | Đủ sáu lỗi, cột dẫn xuất được rebuild, log truy vết được |
| Baseline pipeline | Vinh | Dũng | Exit code 0; artifact và report khớp metrics |
| Repair pipeline | Vinh + Thái | Giang | Rebuild từ raw, chạy lặp ổn định, không sửa vá corrupted data |
| Submission/evidence | Vinh | Cả nhóm | Không secret; đủ report; 100% thành viên có commit và nộp LMS |

## 7. Lệnh nghiệm thu chung

```bash
python -c "import chromadb, great_expectations, sentence_transformers; print('Môi trường sẵn sàng')"
python script/run_phase1.py
python script/run_corruption_flow.py
```

Sau khi chạy, nhóm phải kiểm tra tối thiểu:

```text
data/raw/crossref_response.json
data/raw/crossref_records.json
data/clean/papers_clean.csv
data/clean/papers_clean.json
data/chroma/
data/embeddings/
data/eval/test_set.json
data/quality/
data/results/baseline_metrics.json
data/results/corruption_log.json
data/results/corrupted_metrics.json
data/results/repaired_metrics.json
data/reports/phase1_report.md
data/reports/corruption_report.md
```

## 8. Phân công live demo và Q&A

| Phần trình bày | Người phụ trách | Nội dung phải giải thích được |
|---|---|---|
| Mở đầu và luồng end-to-end | Vinh | Mục tiêu, kiến trúc luồng, cách tái hiện hai pipeline |
| Ingestion và lineage | Giang | API/fallback, raw artifacts, vì sao không sửa raw snapshot |
| Cleaning và benchmark | Đạt | `age_days`, `text_for_embedding`, test set và ground truth IDs |
| Quality/freshness | Dũng | Bốn GX expectations, SLA 180 ngày/25%, cách đọc quality artifact |
| Corruption/repair | Thái | Sáu lỗi, silent failure, idempotent repair từ raw records |
| Bảng ba trạng thái và kết luận | Vinh, Dũng | Metric giảm/phục hồi và bằng chứng hỗ trợ từng kết luận |

Tất cả thành viên phải trả lời được năm câu hỏi chung:

1. Dữ liệu đi từ Crossref đến ChromaDB như thế nào?
2. Test set và ground-truth document IDs được dùng để đo retrieval ra sao?
3. Quality checks khác freshness monitoring ở điểm nào?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Dựa vào artifact/metric nào để kết luận repair thành công?

## 9. Checklist trước khi nộp

- [ ] `python script/run_phase1.py` exit code 0.
- [ ] `python script/run_corruption_flow.py` exit code 0.
- [ ] Raw data có đủ response và parsed records.
- [ ] Clean data có 24 dòng hợp lệ và `paper_id` unique.
- [ ] Test set có 10 câu, đủ bốn nhóm nghiệp vụ.
- [ ] Baseline/corrupted/repaired dùng cùng test set.
- [ ] GX 1.x có đủ bốn expectations và freshness SLA.
- [ ] Corruption log có đủ sáu kịch bản.
- [ ] Có đủ ba file metrics và bảng so sánh ba trạng thái.
- [ ] `group_report.md` đã điền bằng số liệu thực tế.
- [ ] Có năm báo cáo cá nhân theo mẫu `report/individual_report.md`.
- [ ] `docs/TEAM.md` có tên, MSSV, email, vai trò và đóng góp thực tế của năm thành viên.
- [ ] Không có `.env`, API key, token hoặc secret trong Git history/artifacts/report.
- [ ] Không có đường dẫn tuyệt đối của máy cá nhân trong source code.
- [ ] Vinh, Giang, Đạt, Dũng và Thái đều có commit trên nhánh `main`.
- [ ] Mỗi thành viên tự nộp link repo lên VLearn trước hạn.

## 10. Thông tin còn thiếu cần bổ sung

Để hoàn thiện hồ sơ nhóm và `docs/TEAM.md`, cần bổ sung:

- Tên chính thức của nhóm.
- Họ tên đầy đủ, MSSV và email của Vinh, Giang, Đạt, Dũng, Thái.
- URL/tên repository chính thức.
- LLM provider/model nhóm sẽ dùng khi chạy và demo (`mock`, Gemini, OpenAI, Anthropic, Ollama hoặc provider khác).
- Nội dung codelab trên VLearn nếu có yêu cầu bổ sung ngoài các file trong repository.
- Nhóm có chọn hạng mục bonus nào hay chỉ hoàn thành 100 điểm bắt buộc.

## 11. Gợi ý phạm vi bonus sau khi hoàn thành phần bắt buộc

Chỉ triển khai bonus sau khi hai pipeline chính chạy ổn định và phần bắt buộc dự kiến đạt ít nhất 85 điểm:

- **B2 — Auto-repair (+5):** Vinh và Thái mở rộng quality gate để tự động kích hoạt rebuild từ raw khi check fail.
- **B3 — Pytest CI (+5):** Giang, Đạt và Dũng viết test cho ingestion, cleaning, test set và quality; Vinh tích hợp CI.

Tổng điểm bonus tối đa vẫn là 10 điểm. Không ưu tiên dashboard trước khi các artifact, metrics và báo cáo bắt buộc đã hoàn chỉnh.
