# Mapping corruption và quality gate

Tài liệu này mô tả contract hiện tại giữa `src/ingestion/corruption.py` và `src/observability/quality.py`. Mọi kết luận khi demo phải kiểm tra lại trong `data/results/corruption_log.json` và `data/quality/*_quality_report.json` sau khi chạy pipeline.

| Corruption | Tác động trên 24 baseline records | Tín hiệu kiểm tra |
| --- | --- | --- |
| `drop_latest_records` | Xóa `ceil(24 × 0.20) = 5` records mới nhất; chọn ổn định theo `published`, `paper_id` | `ExpectTableRowCountToBeBetween` với min/max = 24 |
| `blank_summary` | Đặt summary thành chuỗi rỗng | `ExpectColumnValueLengthsToBeBetween(summary, min=50)` fail; chuỗi rỗng **không** làm `NotNull` fail |
| `inject_noise` | Chèn token `###CORRUPT###` vào summary | `ExpectColumnValuesToNotMatchRegex(summary)` fail |
| `truncate_title` | Cắt title còn tối đa 7 ký tự | `ExpectColumnValueLengthsToBeBetween(title, min=10)` fail |
| `stale_date` | Đưa published về 400 ngày trước; `age_days` được tính lại từ published | Freshness SLA fail khi tỷ lệ `age_days > 180` vượt 25% |
| `duplicate_rows` | Thêm 3 bản sao cùng `paper_id` | `ExpectColumnValuesToBeUnique(paper_id)` fail |

Quality gate dùng bốn loại GX expectations bắt buộc của rubric: row count, not null, unique, value length. Regex expectation bổ sung phát hiện riêng noise. Baseline và repaired phải pass; corrupted phải fail. `summary_chars`, `age_days` và `text_for_embedding` đều được tính lại sau corruption; `text_for_embedding` gọi cùng `build_embedding_text()` như cleaning.

## Auto-Repair

`run_corruption_flow()` chạy quality gate trên corrupted dataframe **trước khi chọn trạng thái phục vụ**. Khi `success=false`, `auto_repair_if_needed()` tự dựng repaired dataframe từ `data/raw/crossref_records.json`, chạy lại GX/freshness và chỉ dùng collection `papers-repaired` khi gate mới pass. Quyết định được ghi ở `data/results/auto_repair_event.json`; collection đang được chọn nằm trong `data/results/active_state.json`.

Nếu raw snapshot thiếu, schema/ID không khớp baseline, hoặc repaired data vẫn fail, event có `status=failed` và pipeline không quảng bá repaired collection. Nếu corrupted data pass, event có `status=skipped` và không thực hiện repair.
