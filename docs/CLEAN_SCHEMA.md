# Clean data và evaluation-set contract

## Nguồn và quy tắc làm sạch

`build_clean_dataframe` đọc `PaperRecord` từ `data/raw/crossref_records.json`; raw snapshot không bị sửa. `paper_id` là DOI đã trim và chuyển về chữ thường, dùng làm khóa dedup và document ID. Bản ghi thiếu `paper_id`, `title` hoặc `published` hợp lệ bị loại. Kết quả được sắp theo `paper_id` để tái hiện ổn định.

Văn bản được bỏ JATS/XML tags, giải mã HTML entities và chuẩn hóa khoảng trắng. `published` và `updated` lưu dưới dạng chuỗi ngày ISO `YYYY-MM-DD` theo UTC; `updated` thiếu hoặc lỗi dùng `published`. `age_days` là số ngày từ `published` tới ngày chạy UTC. `summary_chars` đếm ký tự của summary sau khi làm sạch.

## Clean schema

| Cột | Kiểu trong JSON | Ý nghĩa |
| --- | --- | --- |
| `paper_id`, `title`, `summary`, `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment` | string | Trường raw đã chuẩn hóa |
| `authors`, `categories` | list[string] | Giá trị nhiều mục đã chuẩn hóa |
| `category_source` | string | `crossref_subject`, `title_rules` hoặc `missing` |
| `age_days`, `summary_chars` | integer | Cột dẫn xuất |
| `authors_joined`, `categories_joined`, `text_for_embedding` | string | Cột dùng cho index, QA và evaluation |

`text_for_embedding` có năm dòng theo thứ tự: `Title`, `Summary`, `Authors`, `Categories`, `Published`. Hàm `build_embedding_text` trong `src/ingestion/cleaning.py` là quy tắc dùng chung; khi corruption đổi bất kỳ trường nào trong năm phần, phải dựng lại text này và các cột dẫn xuất liên quan.

## Nguồn của categories

Snapshot Crossref hiện tại có 24 bản ghi nhưng không bản ghi nào chứa `subject`. Để có câu hỏi evaluation về categories mà không điền tay dữ liệu, cleaning suy ra **nhãn chủ đề** từ các từ khóa rõ ràng trong title. `category_source=title_rules` đánh dấu nguồn dẫn xuất này. Nếu bản ghi tương lai có Crossref `subject`, cleaning ưu tiên subject gốc và đặt `category_source=crossref_subject`. Nhãn suy luận là metadata phục vụ bài lab, không được mô tả như subject do Crossref cung cấp.

## Test set

`build_test_set` tạo 10 câu hỏi từ 10 bài khác nhau: 4 `summary`, 2 `authors`, 2 `date`, 2 `categories`. Mỗi mục có `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids`. Ground truth lấy trực tiếp từ clean dataframe; summary dùng câu đầu tiên của abstract đã làm sạch. Chọn bài theo `published` giảm dần rồi `paper_id` tăng dần, cho kết quả tái hiện được từ cùng baseline.

Chỉ tạo `data/eval/test_set.json` từ baseline một lần. Pipeline baseline, corrupted và repaired phải cùng đọc file này; không sinh lại khi chạy corruption hoặc repair.