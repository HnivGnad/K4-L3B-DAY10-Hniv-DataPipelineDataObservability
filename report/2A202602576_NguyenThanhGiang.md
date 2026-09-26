# Báo cáo cá nhân — Nguyễn Thanh Giang

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Thanh Giang       |
| MSSV               | 2A202602576                |
| Khóa/Lớp         | K4-L3B-DAY10             |
| Tên nhóm         | Hniv                       |
| Vai trò chính    | Source & Data Lineage Owner|
| Repository         | https://github.com/HnivGnad/K4-L3B-DAY10-Hniv-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26                 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Khởi tạo & Fetch data| `src/ingestion/crossref.py::fetch_source_records` | `Settings` params | `data/raw/crossref_response.json` | Hoàn thành |
| Parse & Bóc tách| `src/ingestion/crossref.py::parse_crossref_payload` | `dict` payload | Danh sách 24 `PaperRecord` chuẩn | Hoàn thành |
| Fallback Snapshot| `src/ingestion/crossref.py::load_raw_records` | File snapshot `Path`| Danh sách `PaperRecord` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Giải thích và chốt Schema gốc | Đạt (Cleaning Owner) | Đạt nắm được cấu trúc Raw Schema để phục vụ việc Clean |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Lấy dữ liệu Crossref | `crossref.py` | `crossref_response.json`, `crossref_records.json` | Chạy lệnh `fetch_source_records()` trả về 24 records. |
| Loại bỏ rác HTML/XML | `parse_crossref_payload` | Bản ghi đã được dọn rác các thẻ `<jats:p>` | Kiểm tra trực tiếp file output json. |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
Tạo ra `data/raw/crossref_records.json` chứa đầy đủ 24 bài báo với định danh `DOI` làm `paper_id` ổn định, làm tiền đề cho toàn bộ các module tiếp theo phía sau (Clean, Observability, Repair) có data để chạy.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Crossref API trả về cục JSON rất phức tạp, chứa nhiều thẻ HTML rác và có rủi ro sập do Rate Limit (429) hoặc mất mạng, làm gián đoạn bài lab.

### Cách triển khai
- Dùng `urllib.request` để call API.
- Cài đặt retry + exponential backoff (ngủ lũy thừa `time.sleep(2 ** attempt)`) nếu bị báo 429/503.
- Cài đặt fallback: Nếu lấy thất bại, tự động đọc từ snapshot lưu sẵn `data/raw/crossref_response.json`.
- Trích xuất `DOI` làm `paper_id`, dùng RegEx `re.sub(r"<[^>]+>", "", text)` để khử rác HTML.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Settings cấu hình query, JSON API payload |
| Output                         | Hai file Raw JSON Artifacts, List[PaperRecord] |
| Module phụ thuộc             | `core.config`                             |
| Module sử dụng output        | `ingestion.cleaning` (Đạt)              |
| Điều kiện lỗi cần xử lý | Lỗi HTTP 429, 503, mất kết nối mạng.  |

### Cách xác minh

```bash
$env:PYTHONIOENCODING="utf-8"; python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s=load_settings(); r=fetch_source_records(s); print(f'Tín hiệu hoàn thành: Đã tải {len(r)} bài báo')"
```
- **Kết quả mong đợi:** Tín hiệu hoàn thành: Đã tải 24 bài báo.
- **Kết quả thực tế:** Tín hiệu hoàn thành: Đã tải 24 bài báo.
- **Artifact/log:** `data/raw/crossref_records.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lấy dữ liệu từ Internet dễ gặp lỗi và thiếu tính ổn định cho Reproducibility (Tái hiện).
- **Các phương án đã cân nhắc:** (1) Chỉ lấy online liên tục. (2) Lưu thêm bản Snapshot Offline (Raw preservation).
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Tăng độ ổn định, tiết kiệm call API. Đặc biệt hỗ trợ cơ chế Idempotent Repair sau này (khi dữ liệu lỗi, có thể phục hồi ngay lập tức từ bản Snapshot).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `UnicodeEncodeError: 'charmap' codec can't encode character '\u1ec7'`
- **Lệnh hoặc bước tái hiện:** Chạy lệnh print text tiếng Việt lên console PowerShell.
- **Nguyên nhân gốc:** Windows mặc định dùng encoding `cp1252` thay vì `utf-8` trong terminal.
- **Cách xử lý:** Gán biến môi trường `$env:PYTHONIOENCODING="utf-8"` trước câu lệnh.
- **Điều học được:** Luôn cảnh giác với vấn đề Encoding khi thao tác với text và file trên nhiều hệ điều hành.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
   API Crossref -> Raw JSON (Ingestion) -> Lọc trùng & Tính toán (Cleaning) -> Nối văn bản `text_for_embedding` -> MiniLM Embedding Model -> Vector lưu vào ChromaDB.
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
   Ground-truth Doc ID được so sánh trực tiếp với Doc IDs mà hệ thống Retrieval lấy ra được để tính `hit_rate`. 
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
   Quality checks bắt lỗi tính toàn vẹn (cấu trúc, null, độ dài). Freshness bắt lỗi thời gian thực tế (độ cũ/mới của dữ liệu).
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
   Để có 1 bộ "thước đo chuẩn" (Control Variable). Chỉ khi dùng chung đề thi thì mới so sánh được khách quan điểm số giữa 3 trạng thái.
5. Repair được xem là thành công dựa trên artifact và metric nào?
   Thành công khi các chỉ số Metrics, Quality Score (7/7) và Freshness ở bước Repaired đều phục hồi lại y hệt như bước Baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.00|       0.60|      1.00| Giảm mạnh do nhiễu, phục hồi tốt |
| `mean_token_f1`      |      1.00|     0.6118|      1.00| Câu trả lời sinh ra bị sai lệch khi gặp data bẩn |
| `judge_accuracy`     |      1.00|       0.60|      1.00| Giảm độ chính xác khi Agent trả lời |
| `mean_judge_score`   |      5.00|       3.50|      5.00| Chấm điểm từ LLM giảm xuống rõ rệt |
| Quality checks         |       7/7|        3/7|       7/7| Catch được 4 lỗi cấu trúc trong corrupted |
| Freshness status       |      True|       True|      True| Mặc dù có bài bị cũ (17.39%) nhưng chưa qua 25% |

### Kết luận từ số liệu
1. [Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]. 
   Dữ liệu bị bẩn khiến Quality check tụt từ 7/7 xuống 3/7, Agent bị nhiễu ngữ cảnh dẫn đến `hit_rate` và điểm đánh giá tụt xuống (Silent Failure).
2. [Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi hoặc chưa phục hồi].
   Sử dụng Idempotent Repair từ snapshot gốc, 100% metrics và signal đã phục hồi như cũ.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. Hiểu được vai trò cốt lõi của Data Lineage và Raw Preservation trong Data Engineering.
2. Hiểu được cơ chế Fallback để thiết kế hệ thống có tính chịu lỗi (Fault tolerance).
3. Thấy rõ được RAG LLM dễ bị lừa/ngu đi (Silent Failure) thế nào khi dữ liệu bị "tiêm" rác/nhiễu.

### Nếu có thêm thời gian
Sẽ tạo thêm hệ thống cảnh báo (Alert) bắn notification (VD: Telegram/Email) tự động mỗi khi Fallback được kích hoạt do API lỗi.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thanh Giang
**Ngày xác nhận:** 2026-09-26
