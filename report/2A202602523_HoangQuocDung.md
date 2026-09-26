# Báo cáo cá nhân — Hoàng Quốc Dũng

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Hoàng Quốc Dũng |
| MSSV | 2A202602523 |
| Email | quocdung.work99@gmail.com |
| Lớp / nhóm | K4-L3B-DAY10 / Hniv |
| Vai trò | Data Observability & Reporting Owner |
| Repository | https://github.com/HnivGnad/K4-L3B-DAY10-Hniv-DataPipelineDataObservability |
| Ngày hoàn thành | 2026-09-26 |
| Commit phần việc | `e6c4662` — Add Dung observability and baseline reports |

## 2. Phạm vi công việc

| Phần việc tôi sở hữu | Input | Output | Trạng thái |
| --- | --- | --- | --- |
| Kiểm tra chất lượng bằng Great Expectations 1.x trong `src/observability/quality.py` | Clean dataframe do Đạt tạo | Payload quality và `data/quality/*_quality_report.json` | Hoàn thành |
| Tính độ mới dữ liệu trong `src/observability/quality.py` | `published`, `age_days` và ngưỡng từ `Settings` | `data/quality/freshness_report.json` và trạng thái freshness trong quality report | Hoàn thành |
| Tạo báo cáo Markdown trong `src/observability/reporting.py` | Source summary, metrics, quality và freshness do pipeline truyền vào | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |

Tôi không sở hữu phần lấy dữ liệu Crossref, cleaning, tạo corruption, xây ChromaDB hay tính metrics. Giang, Đạt, Thái và Vinh phụ trách các phần đó; Vinh gọi các hàm của tôi từ hai pipeline.

## 3. Kết quả bàn giao

Tôi dùng API Great Expectations 1.x với ephemeral context, Pandas data source, dataframe asset và batch definition để chạy bốn loại expectation: số dòng, không null, mã bài duy nhất và độ dài văn bản. Bốn loại này được áp dụng thành **7 phép kiểm tra cụ thể** trên bảng và các cột `paper_id`, `title`, `summary`. Hàm trả payload gồm kết quả từng phép kiểm tra và kết luận chung, đồng thời ghi JSON vào `data/quality/`.

Freshness được tính theo `age_days > 180`. Hàm đếm số dòng quá hạn, chia cho tổng số dòng và đặt `is_fresh = False` khi tỷ lệ vượt `0.25`; ngày xuất bản thiếu hoặc tuổi bài không hợp lệ cũng khiến trạng thái không đạt. Báo cáo freshness còn ghi ngày xuất bản mới nhất và cũ nhất.

Hàm tạo báo cáo chỉ đọc các payload được truyền vào để lập bảng Markdown. Báo cáo baseline hiển thị nguồn dữ liệu, bốn metrics chính, bảy phép kiểm tra và freshness. Báo cáo corruption so sánh metrics của baseline, corrupted, repaired; liệt kê các phép kiểm tra thất bại và mức thay đổi của metrics.

| Artifact | Nội dung có thể kiểm tra |
| --- | --- |
| `data/quality/baseline_quality_report.json` | 7/7 phép kiểm tra đạt trên 24 bài |
| `data/quality/corrupted_quality_report.json` | Corrupted đạt 3/7 phép kiểm tra; báo cáo freshness được lưu ở file riêng |
| `data/quality/repaired_quality_report.json` | 7/7 phép kiểm tra đạt sau khi dựng lại từ raw |
| `data/quality/freshness_report.json` | Baseline: 0/24 bài quá 180 ngày, `is_fresh = true` |
| `data/quality/corrupted_freshness_report.json`, `data/quality/repaired_freshness_report.json` | Freshness riêng của dữ liệu corrupted và repaired |
| `data/reports/phase1_report.md` | Bảng baseline từ source summary, metrics, quality và freshness |
| `data/reports/corruption_report.md` | Bảng so sánh ba trạng thái và các quality/freshness signal |

## 4. Cách triển khai, input và output

`run_data_quality_checks(df, settings, report_name)` nhận clean dataframe và cấu hình; hàm kiểm tra các cột bắt buộc trước, sau đó chạy GX trên dataframe trong bộ nhớ. Kết quả được lưu theo `report_name`, ví dụ `baseline` tạo `baseline_quality_report.json`. Hàm `build_freshness_report(df, settings, report_path)` tính các chỉ số độ mới và ghi JSON theo đường dẫn được truyền vào.

`generate_phase1_report(...)` và `generate_corruption_report(...)` nhận dict kết quả, định dạng giá trị và ghi Markdown. Nếu một metric không được cung cấp, báo cáo hiện `N/A` thay vì tự tạo số. Các phép kiểm tra thất bại được liệt kê để người đọc thấy lý do quality gate không đạt.

Input bắt buộc của quality là `paper_id`, `title`, `summary`, `published`, `age_days`; thiếu cột sẽ báo `ValueError` kèm tên cột. Output được `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py` dùng để hoàn tất báo cáo của từng luồng. Cả ba trạng thái dùng chung `data/eval/test_set.json` do Đạt tạo từ baseline.

### Cách tái hiện

Từ thư mục gốc repo, chạy:

```powershell
python script/run_phase1.py
python script/run_corruption_flow.py
```

Hai lệnh trên gọi code quality/reporting qua pipeline và tạo các artifact nêu trên. Log chạy được đối chiếu với các file JSON và Markdown trong `data/quality/`, `data/results/`, `data/reports/`. Báo cáo này không coi các con số được in trong terminal là nguồn duy nhất; artifact là bằng chứng để đọc lại.

## 5. Quyết định kỹ thuật và blocker

**Quyết định:** Tôi dùng GX 1.x trên Pandas dataframe trong bộ nhớ. Phương án còn lại là viết toàn bộ phép kiểm tra bằng biểu thức pandas. GX phù hợp yêu cầu bài lab, cho kết quả theo từng expectation và giúp ghi rõ check nào thất bại. Tôi giữ freshness bằng phép tính riêng vì đây là tỷ lệ trên toàn dataset với quy tắc 180 ngày / 25%, sau đó ghép nó vào kết luận quality gate. Baseline và repaired đạt 7/7 theo JSON quality; corrupted đạt 3/7 theo `corruption_report.md`.

**Blocker tích hợp:** Khi tôi bắt đầu phần này, clean dataframe và baseline metrics chưa có nên chưa thể tạo báo cáo bằng số liệu thật. Tôi hoàn thiện hàm theo clean schema và contract trước; sau khi Đạt và Vinh bàn giao dữ liệu sạch 24 dòng cùng `baseline_metrics.json`, tôi chạy quality/freshness và tạo `phase1_report.md`.

**Lỗi tích hợp đã được nhóm xử lý:** Một phiên bản trước của `src/pipelines/corruption_flow.py` ghi freshness corrupted đè lên `corrupted_quality_report.json`, khiến file mất danh sách GX checks. Nhóm đã tách đường dẫn freshness cho corrupted và repaired trong commit `bf06869`. Trên `origin/main` hiện tại, `corrupted_quality_report.json` chứa kết quả 3/7 và `corrupted_freshness_report.json` lưu riêng tỷ lệ stale. Đây là sửa đổi tích hợp của nhóm, không phải phần code tôi nhận sở hữu.

## 6. Hiểu luồng toàn bài

1. Giang lấy dữ liệu Crossref và giữ bản raw; Đạt làm sạch thành bảng có `text_for_embedding`; Sentence Transformers chuyển văn bản thành vector, rồi ChromaDB lưu chỉ mục để tìm bài liên quan.
2. Bộ 10 câu hỏi có đáp án và `ground_truth_doc_ids`. Retrieval hit rate đo xem bài đúng có nằm trong kết quả tìm kiếm; Token F1 và judge đánh giá câu trả lời so với đáp án.
3. Quality checks xem dữ liệu có đúng cấu trúc và nội dung kỳ vọng không, chẳng hạn đủ dòng và không trùng `paper_id`; freshness tập trung vào tuổi bài báo và tỷ lệ bài quá hạn.
4. Giữ nguyên một test set cho baseline, corrupted và repaired giúp so sánh trên cùng câu hỏi; nếu thay câu hỏi giữa chừng, mức thay đổi metrics không còn phản ánh riêng tác động của dữ liệu.
5. Repair dựng lại dữ liệu từ raw records qua cleaning, rồi đối chiếu số dòng, quality report, freshness report và bốn metrics với baseline. Dữ liệu repaired trong repo trở lại 24 dòng, quality 7/7 và các metrics chính bằng baseline.

## 7. Phân tích số liệu

| Metric / signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6000 | 1.0000 | Corruption làm giảm 0.4; repair phục hồi mức ban đầu |
| `mean_token_f1` | 1.0000 | 0.6118 | 1.0000 | Mức trùng từ của câu trả lời giảm rồi phục hồi |
| `judge_accuracy` | 1.0000 | 0.6000 | 1.0000 | Tỷ lệ trả lời đúng giảm rồi phục hồi |
| `mean_judge_score` | 5.0000 | 3.5000 | 5.0000 | Điểm judge trung bình giảm rồi phục hồi |
| Phép kiểm tra GX đạt | 7/7 | 3/7 | 7/7 | Corrupted fail bốn phép kiểm tra |
| `stale_ratio` | 0/24 = 0% | 4/23 ≈ 17.39% | 0/24 = 0% | Corrupted có bài quá cũ nhưng chưa vượt ngưỡng 25% |
| `is_fresh` | true | true | true | Trạng thái vẫn true theo quy tắc tỷ lệ của bài lab |

Hai chuỗi bằng chứng có thể rút ra từ **toàn bộ trạng thái bị làm lỗi**, không quy mức giảm metrics cho riêng một kịch bản:

1. Sáu thay đổi dữ liệu trong `corruption_log.json` → quality giảm từ 7/7 còn 3/7 và tỷ lệ bài quá cũ tăng → retrieval hit rate giảm từ 1.0 xuống 0.6, Token F1 giảm từ 1.0 xuống 0.6118.
2. Dựng lại clean dataframe từ raw records → quality trở về 7/7, stale ratio trở về 0% → retrieval hit rate, Token F1 và judge accuracy trở về 1.0 trên cùng test set.

Điểm khác kỳ vọng là corruption làm cũ ngày xuất bản nhưng `is_fresh` vẫn true. JSON freshness cho thấy 4/23 dòng quá 180 ngày, tức khoảng 17.39%, chưa vượt ngưỡng 25%; vì vậy đây là kết quả đúng theo quy tắc đã đặt. Chỉ số retrieval giảm rõ rệt, nhưng bộ lỗi được áp dụng cùng lúc nên không thể khẳng định riêng lỗi drop, duplicate hay stale date gây ra bao nhiêu phần trăm mức giảm nếu chưa đo từng lỗi độc lập.

## 8. Điều học được và hướng cải thiện

1. Mỗi bước pipeline cần artifact để có thể truy lại dữ liệu đã thay đổi ở đâu và đối chiếu báo cáo với kết quả thật.
2. Một quality gate nên ghi rõ từng phép kiểm tra đạt hay thất bại; trạng thái chung `success` một mình không đủ để tìm nguyên nhân.
3. Dữ liệu có thể giảm chất lượng trả lời mà pipeline vẫn chạy; cần xem quality signal cùng metrics của agent.

Nếu có thêm thời gian, tôi sẽ chạy từng kịch bản corruption riêng trên cùng test set và ghi một hàng kết quả cho mỗi kịch bản. Cách này giúp xác định lỗi nào thực sự làm giảm từng metric, thay vì chỉ kết luận từ sáu lỗi áp dụng cùng lúc.

## 9. Xác nhận nội dung

Báo cáo này ghi đúng phạm vi code tôi phụ trách và số liệu từ artifact hiện có. Tôi có thể giải thích luồng từ dữ liệu nguồn đến báo cáo, và không nhận phần code ingestion, retrieval, evaluation hay corruption do các thành viên khác sở hữu. Không có API key hoặc token trong báo cáo.

**Hoàng Quốc Dũng — 2026-09-26**
