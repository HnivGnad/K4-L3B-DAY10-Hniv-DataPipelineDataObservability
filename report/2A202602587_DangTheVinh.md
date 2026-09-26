# Báo cáo vai trò thành viên — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đặng Thế Vinh |
| MSSV | 2A202602587 |
| Khóa/Lớp | K4-L3B |
| Tên nhóm | Hniv |
| Vai trò chính | Pipeline Integration & Evidence Owner |
| Repository | [K4-L3B-DAY10-Hniv-DataPipelineDataObservability](https://github.com/HnivGnad/K4-L3B-DAY10-Hniv-DataPipelineDataObservability) |
| Ngày hoàn thành | 2026-09-26 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Baseline orchestration | `src/pipelines/phase1.py`: `run_baseline()`, `main()` và các hàm kiểm tra contract | Raw records của Giang, cleaning/test set của Đạt, quality/reporting của Dũng | Clean artifacts, collection `papers-baseline`, baseline answers/metrics và phase-1 report | Hoàn thành |
| Corruption/repair integration | `src/pipelines/corruption_flow.py`: `run_corruption_flow()`, `_evaluate_state()`, `_repair_from_raw()` | Baseline artifacts, corruption function của Thái, quality/reporting của Dũng | Corrupted/repaired collections, answers, metrics, quality/freshness và comparison report | Hoàn thành |
| Artifact configuration | `src/core/config.py`: các đường dẫn cho ba trạng thái | Cấu trúc deliverable theo đề bài | Đường dẫn tách biệt cho clean data, embeddings, metrics, quality và freshness | Hoàn thành |
| Evidence validation | `data/embeddings/`, `data/results/`, `data/quality/`, `data/reports/` | Artifacts được sinh trực tiếp từ hai pipeline | Bộ bằng chứng định lượng Baseline–Corrupted–Repaired | Hoàn thành |

Các commit chính phản ánh phần việc của tôi:

- `69257f2 baseline index + evaluation`
- `bf06869 fix overwrite`
- `377f228 run test`

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chốt data contract và thứ tự tích hợp | Giang, Đạt, Dũng, Thái | Các module dùng chung `paper_id`, clean schema, test set và `Settings.paths` mà không đổi chữ ký hàm |
| Debug quality/freshness artifact | `observability/quality.py`, phần việc của Dũng | Quality report và freshness report của corrupted/repaired được lưu ở các file độc lập, không còn ghi đè nhau |
| Kiểm chứng corruption đạt SLA | `ingestion/corruption.py`, phần việc của Thái | Corrupted dataset có `stale_ratio = 7/23 = 0.3043`, vượt ngưỡng 0.25 và làm `is_fresh=False` |
| Kiểm thử tích hợp | Toàn bộ data contract và corruption flow | 15 test chạy thành công; hai entrypoint chạy và sinh artifacts đúng contract |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Điều phối baseline từ raw data đến evaluation | `src/pipelines/phase1.py::run_baseline()` | Collection `papers-baseline` gồm 24 documents | `uv run python script/run_phase1.py` |
| Kiểm tra clean dataframe trước khi embedding | `_validate_clean_dataframe()` | Chặn dataframe rỗng, thiếu cột, trùng `paper_id` hoặc thiếu `text_for_embedding` | Pipeline chỉ tiếp tục khi data contract hợp lệ |
| Cố định benchmark dùng chung | `_prepare_test_set()`, `data/eval/test_set.json` | 10 câu thuộc bốn loại, dùng lại cho cả ba trạng thái | Đối chiếu cùng một đường dẫn test set trong hai pipeline |
| Chạy baseline evaluation | `data/results/baseline_metrics.json`, `baseline_answers.json` | Hit rate, Token F1 và judge metrics được sinh tự động | Đọc metrics JSON sau khi chạy phase 1 |
| Tích hợp corrupted/repaired evaluation | `src/pipelines/corruption_flow.py` | Hai collection riêng, hai bộ metrics và answers riêng | `uv run python script/run_corruption_flow.py` |
| Tách freshness artifacts | `src/core/config.py`, `src/pipelines/corruption_flow.py` | Có đường dẫn riêng cho corrupted và repaired freshness | Kiểm tra hai JSON freshness không ghi đè quality JSON |
| Kiểm chứng repair | `_repair_from_raw()` và `data/results/repaired_metrics.json` | Repaired data có 24 records unique; metrics trở về bằng baseline | So sánh baseline và repaired metrics |

Output cụ thể của phần việc tôi phụ trách là bộ baseline evaluation gồm 24 vector documents và 10 câu benchmark. Kết quả đo được là `retrieval_hit_rate=1.0`, `mean_token_f1=1.0`, `judge_accuracy=1.0`, `mean_judge_score=5.0`. Cùng cơ chế evaluation này được sử dụng lại nguyên vẹn cho corrupted và repaired state, nhờ đó phép so sánh có cùng điều kiện đầu vào.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Các module ingestion, cleaning, indexing, evaluation và observability do nhiều thành viên phát triển độc lập. Phần việc của tôi là kết nối chúng thành hai luồng có thể tái hiện, đồng thời bảo đảm mỗi trạng thái dữ liệu có artifact riêng và kết quả so sánh không bị sai lệch do đổi test set hoặc ghi đè file.

Baseline cần thực hiện tuần tự từ raw snapshot đến clean dataframe, vector index, evaluation, quality/freshness và báo cáo. Corruption flow phải dùng lại baseline test set, cô lập corrupted/repaired index, repair từ raw snapshot đáng tin cậy và xuất đủ bằng chứng cho ba trạng thái.

### Cách triển khai

Trong `run_baseline()` tôi triển khai thứ tự:

1. Đọc raw snapshot mặc định; chỉ refresh nguồn khi cấu hình yêu cầu.
2. Gọi cleaning pipeline và kiểm tra data contract trước khi embedding.
3. Lưu cùng một clean dataframe ra CSV và JSON.
4. Build collection `papers-baseline` bằng `all-MiniLM-L6-v2`.
5. Tạo test set khi chưa tồn tại, sau đó giữ cố định file này.
6. Gọi `evaluate_pipeline()` để sinh answers và metrics.
7. Chạy quality/freshness rồi chuyển payload đo được cho reporting.

Trong `run_corruption_flow()` tôi áp dụng cùng một hàm `_evaluate_state()` cho corrupted và repaired data. Mỗi trạng thái có collection, embedding manifest, answers và metrics riêng. Repair không sửa vá corrupted dataframe mà đọc lại `crossref_records.json` rồi chạy lại `build_clean_dataframe()`, do đó kết quả repair có tính idempotent.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `PaperRecord` từ `data/raw/crossref_records.json`; clean dataframe có `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `age_days`, `text_for_embedding`; test set 10 câu |
| Output | Ba ChromaDB collections, ba embedding manifests, ba bộ answers/metrics, quality/freshness JSON và báo cáo Markdown |
| Module phụ thuộc | `ingestion.crossref`, `ingestion.cleaning`, `ingestion.corruption`, `evaluation.testset`, `evaluation.metrics`, `observability.quality`, `observability.reporting`, `retrieval.index` |
| Module sử dụng output | Corruption flow dùng baseline clean data, test set và metrics; reporting dùng metrics cùng quality/freshness payload |
| Điều kiện lỗi cần xử lý | Raw data rỗng; clean dataframe thiếu cột; `paper_id` rỗng/trùng; `text_for_embedding` rỗng; thiếu baseline metrics/test set; quality và freshness dùng trùng output path |

### Cách xác minh

```bash
uv sync --extra dev
uv run python -m pytest tests -q --basetemp .pytest_tmp
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** 15 test pass; hai pipeline exit code 0; có đủ ba collection và artifacts tách biệt.
- **Kết quả thực tế:** 15 test pass. Baseline đạt Hit Rate/F1 bằng 1.0; corrupted giảm còn 0.6/0.6118; repaired phục hồi về 1.0/1.0.
- **Artifact/log:** `data/results/*_metrics.json`, `data/results/*_answers.json`, `data/quality/`, `data/embeddings/`, `data/reports/`; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chứng minh metric thay đổi do data corruption và phục hồi do repair, không phải do đổi benchmark hoặc dùng chung vector state.
- **Các phương án đã cân nhắc:** (1) Rebuild test set và dùng lại một collection cho mỗi lần chạy; (2) giữ nguyên test set và tách ba collection; (3) sao chép kết quả baseline rồi chỉnh dữ liệu trực tiếp trong collection.
- **Phương án đã chọn:** Giữ duy nhất `data/eval/test_set.json` và dùng ba collection `papers-baseline`, `papers-corrupted`, `papers-repaired`.
- **Lý do:** Cùng test set giúp phép đo có kiểm soát; collection tách biệt ngăn dữ liệu từ trạng thái trước tồn tại trong trạng thái sau; việc delete/recreate collection theo tên giúp chạy lặp lại mà không tích lũy documents.
- **Bằng chứng quyết định phù hợp:** Corrupted Hit Rate giảm từ 1.0 xuống 0.6, sau đó repaired trở lại đúng 1.0 trên cùng 10 câu. Ba embedding manifests đều ghi đúng collection và số documents tương ứng 24/23/24.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Sau corruption flow, `data/quality/corrupted_quality_report.json` không còn các trường `success` và `checks`; file chỉ chứa các trường freshness. Freshness của corrupted data ban đầu vẫn trả về `is_fresh=True` dù đã tiêm stale-date corruption.
- **Lệnh hoặc bước tái hiện:** Chạy `uv run python script/run_corruption_flow.py`, sau đó đọc `corrupted_quality_report.json` và kiểm tra `stale_ratio`.
- **Nguyên nhân gốc:** `build_freshness_report()` được truyền cùng đường dẫn với corrupted quality report nên ghi đè JSON đã sinh bởi GX. Đồng thời stale-date chỉ sửa ba records, chưa đủ làm tỷ lệ stale vượt ngưỡng 25% sau drop/duplicate.
- **Cách xử lý:** Thêm `corrupted_freshness_report` và `repaired_freshness_report` vào `Settings.paths`; sửa corruption flow dùng hai đường dẫn riêng. Số records stale được tính theo kích thước dataset cuối dự kiến để tỷ lệ luôn lớn hơn 0.25.
- **Cách xác minh sau khi sửa:** 15 test pass; corrupted quality JSON giữ đủ 7 checks; corrupted freshness có `stale_rows=7`, `total_rows=23`, `stale_ratio=0.3043`, `is_fresh=false`; repaired freshness có `0/24`, `is_fresh=true`.
- **Điều học được:** Artifact path cũng là một phần của data contract. Hai phép đo đúng về logic vẫn có thể tạo bằng chứng sai nếu cùng ghi vào một file. Corruption test cần kiểm tra ngưỡng nghiệp vụ thực tế, không chỉ kiểm tra có ít nhất một dòng lỗi.

## 7. Hiểu biết về luồng end-to-end

1. Crossref payload được parse thành `PaperRecord` và lưu raw snapshot. Cleaning loại XML/khoảng trắng, chuẩn hóa schema, tính `age_days`, deduplicate và tạo `text_for_embedding`. MiniLM biến text thành vector chuẩn hóa và ChromaDB lưu vector cùng metadata trong collection tương ứng.
2. Mỗi câu trong evaluation set chứa câu hỏi, đáp án chuẩn và `ground_truth_doc_ids`. Retrieval hit khi top-k có ít nhất một ground-truth ID. Câu trả lời được so sánh với ground truth bằng Token F1 và judge score.
3. Quality checks kiểm tra cấu trúc và tính hợp lệ như số dòng, null, uniqueness và độ dài. Freshness monitoring tập trung vào độ tuổi dữ liệu: record stale khi `age_days > 180`, dataset fail khi tỷ lệ stale vượt 25%.
4. Nếu đổi test set giữa baseline, corrupted và repaired thì không thể tách ảnh hưởng của corruption khỏi độ khó của benchmark. Dùng cùng test set tạo một phép thử có kiểm soát.
5. Repair thành công khi dữ liệu được rebuild từ raw snapshot, khôi phục 24 `paper_id` unique, quality/freshness pass và các metric retrieval/answer quay về mức baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Corruption làm 4/10 câu mất ground-truth document trong top-4; repair phục hồi toàn bộ |
| `mean_token_f1` | 1.0000 | 0.6118 | 1.0000 | Retrieval sai kéo câu trả lời lệch khỏi reference; rebuild index phục hồi hoàn toàn |
| `judge_accuracy` | 1.0000 | 0.6000 | 1.0000 | Tỷ lệ câu đúng giảm tương ứng với retrieval hit rồi quay về baseline |
| `mean_judge_score` | 5.0000 | 3.4000 | 5.0000 | Chất lượng câu trả lời giảm rõ trên corrupted state |
| Quality checks | 7/7 pass | 3/7 pass, gate fail | 7/7 pass | GX phát hiện sai row count, duplicate ID, title ngắn và summary lỗi |
| Freshness status | Fresh, 0/24 stale | Fail, 7/23 stale (30.43%) | Fresh, 0/24 stale | Corruption vượt SLA 25%; repair khôi phục freshness |

### Kết luận từ số liệu

1. Drop latest records, duplicate IDs, blank/truncated/noisy content và stale dates → quality gate fail, freshness từ `True` thành `False` → Hit Rate giảm 1.0 xuống 0.6 và Token F1 giảm 1.0 xuống 0.6118.
2. Rebuild từ raw snapshot → row count/uniqueness/content/freshness trở lại contract sạch → Hit Rate, Token F1 và judge metrics phục hồi bằng baseline.

Corruption ảnh hưởng trực tiếp nhất đến retrieval là `drop_latest_records`, vì document ground truth bị xóa khỏi corpus thì retriever không thể trả lại document đó. Duplicate rows và nội dung bị blank/noise tiếp tục làm không gian vector kém phân biệt. Vì sáu kịch bản được áp dụng trong cùng một suite, kết luận định lượng được đưa ra cho tác động tổng hợp; muốn định lượng riêng từng lỗi cần chạy ablation theo từng scenario.

Kết quả khác kỳ vọng ban đầu là việc đặt cố định ba stale records chưa đủ vượt SLA 25% trên dataset sau drop/duplicate. Tôi kiểm tra tỷ lệ thực tế, thay đổi target count theo kích thước cuối dự kiến và bổ sung assertion `stale_ratio > 0.25`. Kết quả sau sửa là 7/23 records stale, tương đương 30.43%, nên freshness gate fail đúng thiết kế.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Pipeline tích hợp cần contract rõ cho schema, ID, artifact path và trạng thái; kiểm tra sớm giúp lỗi không truyền tới embedding/evaluation.
2. Observability không chỉ là tính metric mà còn phải lưu bằng chứng độc lập, tránh ghi đè và kiểm tra đúng ngưỡng nghiệp vụ.
3. Data corruption có thể không làm chương trình crash nhưng vẫn làm RAG trả lời sai; phải đo cả retrieval, answer quality và quality/freshness signal để phát hiện silent failure.

### Nếu có thêm thời gian

Tôi sẽ bổ sung ablation runner chạy từng corruption riêng biệt trên cùng test set, sau đó tạo bảng mức giảm metric theo scenario. Cải thiện được đo bằng khả năng quy trách nhiệm rõ mỗi lỗi cho thay đổi trong GX signal, Hit Rate và Token F1, thay vì chỉ có tác động tổng hợp của sáu lỗi.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi chỉ ghi “đã chạy thành công” cho phần đã được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đặng Thế Vinh  
**Ngày xác nhận:** 2026-09-26
