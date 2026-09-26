# K4-L3B-Day10 — Data Pipeline & Data Observability for RAG

> **Hình thức:** Teamwork | **Thời lượng:** 240 phút  
> **Lịch học (Lớp B - Ca Sáng):** Thứ 7 (26/09/2026) 09:00 – 13:00  
> ⏰ **Hạn nộp LMS:** 23:59:59 cùng ngày

---

## 🧭 Đọc gì, theo thứ tự nào?

| # | Tài liệu | Mô tả |
|:---:|---|---|
| 1️⃣ | **Codelab trên VLearn LMS** | Hướng dẫn từng bước + nộp bài (mở trên trình duyệt) |
| 2️⃣ | [CHECKPOINTS.md](docs/CHECKPOINTS.md) | Phân bổ thời gian 240 phút & deliverables từng mốc |
| 3️⃣ | [RUBRIC.md](docs/RUBRIC.md) | Tiêu chí chấm điểm (100 chuẩn + 10 bonus) |
| 4️⃣ | [SUBMISSION.md](docs/SUBMISSION.md) | Nội quy, deadline, bảo mật & checklist nộp bài |
| 5️⃣ | [TEAM.md](docs/TEAM.md) | Điền thông tin nhóm & báo cáo cá nhân |

---

## Repo có sẵn gì? (Scaffolded Baseline)

- `data/raw/` — Snapshot offline Crossref API (`crossref_response.json`)
- `src/` — Khung pipeline thu thập, embedding MiniLM, đánh giá metrics (có `TODO(student)`)
- `script/` — Entrypoints: `run_phase1.py`, `run_corruption_flow.py`

## Học viên cần làm gì?

1. Hoàn thiện **Data Quality Gate** (Great Expectations 1.x) trong `src/observability/quality.py`
2. Tích hợp **Freshness Check** (`age_days`) vào Quality Gate
3. Chạy **Baseline → Corruption → Repair** → xuất bảng đối chiếu 3 trạng thái
4. **Live Demo** trên bảng & nộp link repo lên VLearn LMS

## Chạy lại bằng môi trường hiện có

Sau khi cài dependencies từ `uv.lock` hoặc `requirements.txt`, dùng môi trường Python của project để chạy. Các lệnh dưới đây sử dụng snapshot đã lưu, mô hình embedding đã cache và provider `mock`; không cần API key hay gọi lại Crossref.

```bash
HF_HUB_OFFLINE=1 LLM_PROVIDER=mock REFRESH_SOURCE=false REFRESH_TEST_SET=false RUN_RAGAS=false .venv/bin/python script/run_phase1.py
HF_HUB_OFFLINE=1 LLM_PROVIDER=mock REFRESH_SOURCE=false REFRESH_TEST_SET=false RUN_RAGAS=false .venv/bin/python script/run_corruption_flow.py
.venv/bin/python -m pytest -q
HF_HUB_OFFLINE=1 LLM_PROVIDER=mock .venv/bin/python script/run_ui.py
```

Nếu máy chưa cache `all-MiniLM-L6-v2`, bỏ `HF_HUB_OFFLINE=1` ở lần chạy đầu để tải mô hình. `script/run_ui.py` dùng đúng Python của môi trường đang gọi script.

Quality gate kiểm tra GX và freshness trước khi chọn collection phục vụ. Khi corrupted state fail, Auto-Repair dựng lại từ `data/raw/crossref_records.json`, kiểm tra hash/schema/ID và chạy lại gate. Xem [quy tắc corruption và repair](docs/CORRUPTION_GX_MAPPING.md), [sự kiện Auto-Repair](data/results/auto_repair_event.json) và [trạng thái đang phục vụ](data/results/active_state.json).

Metrics offline dùng trả lời trích xuất theo kết quả semantic retrieval. Trường `judge_fallback_count` cho biết số câu được chấm bằng heuristic vì không có LLM judge; không nên diễn giải đó là điểm chấm của LLM.
