# Báo cáo cá nhân — Nguyễn Tất Đạt

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Tất Đạt |
| MSSV | 2A202602578 |
| Email | dat111104@gmail.com |
| Tên Git/GitHub dùng khi đối chiếu | Nguyen Dat / Gaohonggg |
| Author trong Git history | `Nguyen Dat/ Gaohonggg <dat111104@gmail.com>` |
| Khóa/Lớp, nhóm | K4-L3B-DAY10, Hniv |
| Vai trò chính | Cleaning & Evaluation-set Owner |
| Repository nhóm | https://github.com/HnivGnad/K4-L3B-DAY10-Hniv-DataPipelineDataObservability |
| Ngày lập báo cáo | 2026-09-26 |

Git history trên nhánh `main` ghi nhận các commit của tôi: `e590b6d` (cleaning, test set, clean artifacts và test), `94c362f` (clean schema contract), `10895d9` (rà soát rubric, hỗ trợ tích hợp và kiểm chứng pipeline/UI/Auto-Repair). Tên `Gaohonggg` là tên GitHub do tôi cung cấp; Git commit hiển thị author `Nguyen Dat`.

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu chính

| Module/deliverable | File/hàm phụ trách | Input | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cleaning và data modeling | `src/ingestion/cleaning.py`: `build_clean_dataframe()`, `build_embedding_text()` | 24 `PaperRecord` từ snapshot của Giang | `data/clean/papers_clean.csv`, `.json` với 24 `paper_id` duy nhất; văn bản embedding năm phần | Hoàn thành, đã kiểm chứng |
| Evaluation set | `src/evaluation/testset.py`: `build_test_set()` | Clean dataframe | `data/eval/test_set.json` gồm 10 câu và ground truth lấy từ dữ liệu sạch | Hoàn thành, đã kiểm chứng |
| Data contract và kiểm thử | `docs/CLEAN_SCHEMA.md`, `tests/test_data_contract.py` | Raw/clean schema, yêu cầu rubric | Tài liệu mô tả trường dữ liệu, nguồn categories và các kiểm tra cleaning/test set | Hoàn thành |

Raw ingestion là phần Giang bàn giao; Vinh phụ trách orchestration và vector index; Dũng phụ trách GX/reporting; Thái phụ trách corruption. Các module của tôi cung cấp clean schema và test set cho những bước kế tiếp.

### Hỗ trợ tích hợp ngoài phạm vi chính

Commit `10895d9` ghi nhận phần rà soát và sửa tích hợp: evaluation dùng semantic retrieval khi đo Hit Rate, đồng bộ `text_for_embedding` sau corruption với hàm cleaning, bổ sung phát hiện noise, điều kiện kích hoạt Auto-Repair từ quality gate, và sửa dashboard/chat để đọc đúng artifact. Tôi cũng bổ sung test cho Auto-Repair và mock Agent. Đây là công việc hỗ trợ tích hợp trên các module do thành viên khác sở hữu, không thay đổi phân công owner chính của nhóm.

## 3. Kết quả theo vai trò và bằng chứng

| Công việc | Kết quả hiện có | Bằng chứng kiểm tra |
| --- | --- | --- |
| Làm sạch raw snapshot | 24 raw records → 24 clean rows; 24 `paper_id` duy nhất | `data/raw/crossref_records.json`, `data/clean/papers_clean.json` |
| Chuẩn hóa nội dung | Bỏ JATS/XML tags, giải mã HTML entities, chuẩn hóa khoảng trắng; ngày ở dạng ISO; `age_days` và `summary_chars` tính từ dữ liệu đã làm sạch | `src/ingestion/cleaning.py`, `docs/CLEAN_SCHEMA.md`, `tests/test_data_contract.py` |
| Tạo nội dung embedding | Cả 24 dòng có đúng năm phần `Title`, `Summary`, `Authors`, `Categories`, `Published` | `data/clean/papers_clean.json`, `build_embedding_text()` |
| Tạo benchmark | 10 câu trên 10 bài khác nhau: 4 summary, 2 authors, 2 date, 2 categories | `data/eval/test_set.json`, `tests/test_data_contract.py` |
| Kiểm chứng tích hợp | Baseline và repaired có Hit Rate 1.0; corrupted 0.5; quality lần lượt 8/8, 3/8, 8/8 | `data/results/*_metrics.json`, `data/quality/*_quality_report.json` |

Raw snapshot hiện tại **không có `subject` cho cả 24 records**. Vì vậy, `categories` trong clean data được suy luận bằng quy tắc từ từ khóa trong tiêu đề và gắn `category_source=title_rules`. Đây là nhãn chủ đề dẫn xuất phục vụ bài lab, **không phải Crossref subject gốc**. Nếu record sau này có `subject`, cleaning ưu tiên trường nguồn và gắn `category_source=crossref_subject`.

## 4. Giải thích kỹ thuật

### Vấn đề và cách triển khai

Raw Crossref có abstract dạng JATS, trường thiếu và các kiểu dữ liệu chưa phù hợp để index hoặc tạo câu hỏi. Tôi chuyển từng `PaperRecord` thành schema cố định: chuẩn hóa DOI về chữ thường để làm `paper_id`, bỏ record thiếu ID/title/ngày xuất bản hợp lệ, làm sạch text và list tác giả/chủ đề, tính ngày cập nhật dự phòng từ `published`, rồi khử trùng lặp theo `paper_id` và sắp thứ tự ổn định. `text_for_embedding` được dựng từ năm trường theo cùng một hàm để downstream có thể tái sử dụng contract.

`build_test_set()` kiểm tra schema và tính duy nhất của `paper_id`, chọn mười bài khác nhau theo ngày xuất bản giảm dần rồi theo ID. Mỗi câu có `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`. Ground truth lấy trực tiếp từ dòng clean tương ứng; câu hỏi summary dùng câu đầu của abstract. Hàm bỏ qua ứng viên không có đáp án hợp lệ hoặc title chứa dấu nháy đơn để câu hỏi có cấu trúc ổn định. Test set được tạo ở baseline và dùng lại nguyên file khi chạy corrupted/repaired.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `list[PaperRecord]` từ `data/raw/crossref_records.json`, `run_date` UTC |
| Output cleaning | Pandas dataframe với `paper_id`, `title`, `summary`, `authors`, `categories`, `category_source`, `published`, `age_days`, `summary_chars`, các trường joined và `text_for_embedding` |
| Output evaluation set | JSON 10 câu, mỗi câu có một `ground_truth_doc_ids` trỏ tới ID trong clean data |
| Module dùng output | `retrieval.index`, `evaluation.metrics`, `observability.quality`, `ingestion.corruption`, hai pipeline orchestration |
| Trường hợp lỗi | Bỏ raw record thiếu ID/title/ngày hợp lệ; từ chối tạo test set nếu thiếu cột, ID trùng hoặc không đủ 10 bài có đáp án |

### Cách xác minh đã chạy

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
HF_HUB_OFFLINE=1 LLM_PROVIDER=mock REFRESH_SOURCE=false REFRESH_TEST_SET=false RUN_RAGAS=false .venv/bin/python script/run_phase1.py
HF_HUB_OFFLINE=1 LLM_PROVIDER=mock REFRESH_SOURCE=false REFRESH_TEST_SET=false RUN_RAGAS=false .venv/bin/python script/run_corruption_flow.py
```

Kết quả trên môi trường `.venv` có sẵn: **23 test pass**, hai pipeline exit code 0. Baseline/repaired index có 24 tài liệu, corrupted index có 22. Đây là lượt chạy offline từ raw snapshot và embedding model đã cache; không kiểm chứng gọi API của LLM thật. Các artifact cần đối chiếu là `data/clean/`, `data/eval/test_set.json`, `data/results/`, `data/quality/` và `data/reports/`.

## 5. Quyết định kỹ thuật quan trọng

- **Bối cảnh:** Rubric yêu cầu hai câu hỏi `categories`, nhưng 24 raw records không chứa `subject` hoặc `primary_category` có giá trị.
- **Phương án cân nhắc:** (1) để categories rỗng và không thể tạo câu hỏi có đáp án; (2) điền nhãn thủ công, khó truy vết; (3) suy luận bằng quy tắc từ title và ghi rõ nguồn dẫn xuất.
- **Phương án chọn:** Ưu tiên subject gốc nếu có; nếu thiếu, suy luận nhãn từ title, lưu `category_source=title_rules`.
- **Lý do:** Test set có ground truth không rỗng và có thể tái tạo, đồng thời không trình bày nhãn suy luận như dữ liệu Crossref.
- **Bằng chứng:** 24/24 clean rows có `category_source=title_rules`; test set có đúng hai câu categories với đáp án lấy từ `categories_joined`.

## 6. Lỗi hoặc blocker đã xử lý

- **Triệu chứng:** Snapshot raw đủ 24 records nhưng câu hỏi categories không có ground truth vì trường `subject` trống.
- **Bước tái hiện:** Kiểm tra `data/raw/crossref_records.json` rồi tạo test set từ clean dataframe khi `categories_joined` rỗng.
- **Nguyên nhân:** Nguồn Crossref snapshot không cung cấp `subject`; đây là thiếu dữ liệu nguồn, không phải lỗi parse.
- **Cách xử lý:** Bổ sung fallback chủ đề từ từ khóa trong title, ưu tiên subject nguồn nếu về sau có dữ liệu; ghi rõ `category_source` trong schema và test.
- **Kiểm chứng:** `tests/test_data_contract.py` kiểm tra thứ tự ưu tiên của subject nguồn và tính ổn định của test set; artifact hiện có đủ bốn `question_type`.
- **Điều học được:** Khi tạo ground truth dẫn xuất, cần lưu provenance để phân biệt dữ liệu nguồn và dữ liệu do pipeline suy ra.

Trong lượt rà soát tích hợp, tôi còn phát hiện evaluation trước đó có đường tắt lookup theo title chính xác, làm Hit Rate không phản ánh đầy đủ vector retrieval. Commit `10895d9` tắt đường tắt này khi đánh giá và bổ sung test `VectorOnlyIndex`; kết quả corrupted Hit Rate hiện là 0.5 thay vì số cũ 0.6. Đây là tác động của **toàn bộ corruption suite**, không thể quy phần giảm cho một lỗi riêng lẻ nếu chưa chạy ablation.

## 7. Hiểu biết về luồng end-to-end

1. Giang tải/parse Crossref và lưu raw response cùng raw records. Cleaning của tôi tạo clean dataframe và `text_for_embedding`; MiniLM chuyển text thành vector, ChromaDB lưu ba collection riêng cho baseline, corrupted và repaired.
2. Mỗi câu trong test set có đáp án và ground-truth paper ID. Hit Rate kiểm tra ID đúng có trong top-K vector retrieval; Token F1 so token của đáp án dự đoán với ground truth. Ba trạng thái đọc cùng `data/eval/test_set.json` để độ khó benchmark không đổi.
3. GX kiểm tra số dòng, null, uniqueness, độ dài và token noise; freshness kiểm tra tỷ lệ record có `age_days > 180` so với ngưỡng 25%. Cả hai cùng quyết định quality gate.
4. Corruption thay đổi dữ liệu rồi được đánh giá để đo tác động. Nếu gate fail, Auto-Repair dựng lại từ raw snapshot, xác minh hash/schema/ID, kiểm tra GX/freshness lần nữa, re-index và chỉ chọn repaired collection sau khi đạt.
5. Repair được xem là thành công khi event có `status=repaired`, active state là `repaired`, dữ liệu và index về 24 bài, quality/freshness pass, metrics phục hồi trên cùng 10 câu.

## 8. Phân tích kết quả hiện tại

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.5000 | 1.0000 | 5/10 câu corrupted không tìm được ground-truth ID trong top-K |
| `mean_token_f1` | 1.0000 | 0.5321 | 1.0000 | Đáp án trích xuất lệch khi retrieval trả về bài không đúng |
| `judge_accuracy` | 1.0000 | 0.5000 | 1.0000 | Kết quả từ heuristic fallback, không phải LLM judge |
| `mean_judge_score` | 5.0000 | 3.0000 | 5.0000 | Cũng dùng heuristic fallback |
| GX checks pass | 8/8 | 3/8 | 8/8 | Corrupted fail row count, uniqueness, title/summary length và noise regex |
| Freshness | 0/24 stale, đạt | 8/22 stale (36.36%), fail | 0/24 stale, đạt | Corrupted vượt SLA 25% |

Corruption suite làm mất năm record mới nhất, tạo thêm duplicate và thay đổi nội dung/ngày. GX/freshness phát hiện trạng thái bẩn; Hit Rate giảm 0.5 và Token F1 giảm khoảng 0.468. Auto-Repair dựng lại từ raw snapshot, đưa quality lên 8/8 và metrics trở lại baseline. Vì sáu lỗi được áp dụng cùng lúc, bảng này chỉ đo tác động tổng hợp. `judge_fallback_count=10` ở cả ba metrics JSON, nên các cột judge cần đọc như điểm heuristic của lượt chạy offline.

Điểm khác kỳ vọng ban đầu là corruption trước đây chỉ xóa bốn bài vì dùng làm tròn xuống 20% của 24, khiến số dòng và Hit Rate khác bản hiện tại. Contract hiện dùng `ceil(24 × 0.20)=5`; log hiện tại ghi baseline 24, corrupted 22 sau khi cộng ba duplicate. Các báo cáo cũ ghi 23 dòng, 7 checks hoặc Hit Rate 0.6 cần được đồng bộ trước khi nhóm nộp.

## 9. Điều học được và hướng cải thiện

1. Clean schema là contract chung: nếu cột dẫn xuất không được dựng lại sau corruption, vector index, quality check và evaluation có thể nhìn ba phiên bản dữ liệu khác nhau.
2. Ground truth cần provenance. Title-derived categories giải quyết thiếu dữ liệu nhưng phải được phân biệt với subject do Crossref cung cấp.
3. Đo chất lượng RAG cần kiểm tra cả retrieval lẫn câu trả lời; lookup chính xác theo title có thể che tác động của dữ liệu bẩn lên semantic search.

Nếu có thêm thời gian, tôi sẽ tạo một bộ kiểm tra ablation chạy từng corruption riêng trên cùng test set, ghi Hit Rate/F1 và GX signal cho từng lỗi. Khi có provider thật, tôi sẽ chạy thêm LLM judge và đối chiếu với heuristic fallback; không thay tên metric để che nguồn chấm điểm.

## 10. Xác nhận trước khi nộp

- [x] Các đóng góp và commit nêu trong báo cáo đã đối chiếu với Git history.
- [x] Số liệu trong bảng đã đối chiếu với artifact JSON hiện tại.
- [x] Báo cáo không chứa API key, token hoặc nội dung `.env`.

**Người báo cáo:** Nguyễn Tất Đạt  
**Ngày lập:** 2026-09-26
