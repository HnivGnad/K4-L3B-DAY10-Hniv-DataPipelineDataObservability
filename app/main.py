"""Day 10 — Hniv demo UI main entry (Streamlit multi-page)."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.state import STATES, list_documents, semantic_search


PAGE_CONFIG = {
    "page_title": "Day 10 — RAG Observability Demo",
    "page_icon": "📚",
    "layout": "wide",
    "initial_sidebar_state": "expanded",
}


def _overview_page() -> None:
    st.title("📚 Day 10 — RAG Observability Demo")
    st.markdown(
        """
**Nhóm:** Hniv · K4-L3B-DAY10

Bài lab gồm 3 trạng thái pipeline: **Baseline → Corrupted → Repaired**.
UI này chỉ **đọc artifacts đã có** trong `data/`, không thay đổi `src/`.
Tất cả số liệu trên màn hình đều được sinh bởi `run_phase1.py` và `run_corruption_flow.py`.
"""
    )
    st.subheader("🔁 5 tab")
    cols = st.columns(5)
    descriptions = [
        ("📚 Paper Explorer", "Browse 24 papers ở 3 trạng thái, semantic search."),
        ("📊 Quality Dashboard", "GX checks pass/fail + Freshness SLA."),
        ("🔀 State Compare", "Bảng Baseline/Corrupted/Repaired với delta."),
        ("💬 Ask the Corpus", "Chat với Gemini qua retrieval — chọn state."),
        ("🏛 Kiến trúc", "Sơ đồ luồng + files đã chạy."),
    ]
    for col, (title, desc) in zip(cols, descriptions):
        with col:
            st.markdown(f"**{title}**")
            st.caption(desc)

    st.divider()
    st.subheader("🛠 Stack")
    st.code(
        "Pipeline: Python 3.11 · LangChain · ChromaDB · sentence-transformers\n"
        "Quality: Great Expectations 1.x · Freshness SLA\n"
        "UI: Streamlit · Altair · Gemini 2.5-flash (langchain-google-genai)",
        language="text",
    )


def _explorer_page() -> None:
    st.title("📚 Paper Explorer")
    state = st.radio("State", STATES, horizontal=True, key="explorer_state")
    docs = list_documents(state)
    st.caption(f"{len(docs)} papers trong state **{state}**")

    query = st.text_input("Semantic search (để trống = hiện tất cả)", key="explorer_query")
    if query.strip():
        hits = semantic_search(state, query, top_k=10)
        rows = [
            {
                "paper_id": h["paper_id"],
                "title": h["title"],
                "score": round(h["score"], 4),
            }
            for h in hits
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        for hit in hits[:5]:
            with st.expander(f"📄 {hit['title'][:80]}  (score: {hit['score']:.4f})"):
                st.markdown(f"**paper_id:** `{hit['paper_id']}`")
                st.markdown(f"**Score:** `{hit['score']:.4f}`")
                st.code(hit["content"][:600] + ("…" if len(hit["content"]) > 600 else ""), language="text")
    else:
        rows = [{"paper_id": doc["paper_id"], "title": doc["title"]} for doc in docs]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        selected = st.selectbox(
            "Chọn paper để xem chi tiết",
            options=[doc["paper_id"] for doc in docs],
            format_func=lambda pid: next((d["title"][:80] for d in docs if d["paper_id"] == pid), pid),
        )
        if selected:
            doc = next(d for d in docs if d["paper_id"] == selected)
            st.markdown(f"### {doc['title']}")
            st.markdown(f"**paper_id:** `{doc['paper_id']}`")
            st.code(doc["content"], language="text")


def _architecture_page() -> None:
    st.title("🏛 Kiến trúc")
    st.markdown(
        """
```
Crossref API  →  raw snapshot  →  clean dataframe  →
                                  ↓
                ┌─────────────────┴──────────────────┐
                ↓                                     ↓
           baseline                 corrupt(idempotent repair)── rebuild from raw
                ↓                                     ↓
        ChromaDB papers-baseline         ChromaDB papers-corrupted + papers-repaired
                ↓                                     ↓
              GX + Freshness ─────────→ cùng test set 10 câu
                                            ↓
                                  eval(Baseline/Corrupted/Repaired)
                                            ↓
                              data/results/{baseline,corrupted,repaired}_metrics.json
                                            ↓
                                   data/reports/*.md
```
"""
    )
    st.markdown("### Files đã được UI đọc (chỉ đọc, không sửa)")
    read_only = [
        "data/raw/crossref_records.json",
        "data/clean/papers_clean{,_corrupted,_repaired}.{csv,json}",
        "data/embeddings/papers_embeddings{,_corrupted,_repaired}.json",
        "data/quality/{baseline,corrupted,repaired}_quality_report.json",
        "data/quality/freshness_report.json",
        "data/results/{baseline,corrupted,repaired}_metrics.json",
        "data/results/{baseline,corrupted,repaired}_answers.json",
        "data/results/corruption_log.json",
        "data/reports/{phase1_report,corruption_report}.md",
        "data/eval/test_set.json",
    ]
    for line in read_only:
        st.code(line, language="text")


def _chat_page() -> None:
    from app import chat as chat_mod

    st.title("💬 Ask the Corpus")
    st.caption("Câu hỏi được retrieve từ ChromaDB collection rồi Gemini trả lời trên top-K context.")

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.markdown("### Cấu hình")
        state = st.radio("State", STATES, key="chat_state", horizontal=True)
        examples = [
            # --- Câu hỏi chung (chạy được trên cả 3 state) ---
            "Who authored 'Chatbot Hybrid Fatwa MUI Menggunakan Retrieval Augmented Generation dan Large Language Model'?",
            "When was 'Agentic Retrieval-Augmented Generation for Verifiable Regulatory Compliance in Urban Cyber-Physical Systems' published?",
            "What does the abstract of 'DOLPHIN: A Privacy-Preserving Digital Investigation Readiness Assessment Framework' say?",
            "What categories are listed for 'Advances in Reinforcement Learning for Retrieval-Augmented Generation in Large Language Model'?",
            # --- Nhóm 1: Sanity check — câu trả lời nên ổn định cả 3 state ---
            "Summarize the main contribution of 'A Survey on Retrieval-Augmented Generation for Large Language Models'.",
            "Which paper in the corpus discusses hallucination mitigation in RAG systems?",
            # --- Nhóm 2: Stress-test các trường thường bị corruption (authors / date / category) ---
            "List the authors and the exact publication date of 'MedGraphRAG: Graph-based Retrieval-Augmented Generation for Medical Question Answering'.",
            "What is the publication date and primary category of 'Privacy-Preserving Retrieval-Augmented Generation for Personal Data' (if present)?",
            # --- Nhóm 3: Khai thác sự khác biệt về mặt nội dung giữa corrupted vs repaired ---
            "Find papers whose title contains the keyword 'retrieval-augmented' and list their categories.",
            "How many papers in this corpus are categorized under 'cs.CL' (Computation and Language)?",
            # --- Nhóm 4: Câu hỏi phụ thuộc state (repaired có, baseline có thể khác, corrupted hay thiếu/lệch) ---
            "According to the corpus, who are the authors of the paper about 'Graph Neural Network' based retrieval?",
            "Show any paper related to 'evaluation benchmark' for RAG — return title, authors, and publication date.",
        ]
        example = st.selectbox("Câu hỏi mẫu", ["(tự nhập)"] + examples)
        top_k = st.slider("top_k", min_value=1, max_value=8, value=4)
        st.divider()
        if st.button("🗑 Reset lịch sử chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if msg.get("hits"):
                with st.expander(f"📎 {len(msg['hits'])} nguồn đã retrieve"):
                    for idx, hit in enumerate(msg["hits"], start=1):
                        st.markdown(
                            f"**[{idx}]** {hit.title[:90]}  \n"
                            f"`paper_id={hit.paper_id}` · "
                            f"`score={hit.score:.4f}`"
                        )

    prompt_input = example if example != "(tự nhập)" else None
    user_msg = st.chat_input("Nhập câu hỏi của bạn…")
    question = prompt_input or user_msg

    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner(f"Đang retrieve + gọi Gemini trên state = `{state}` …"):
            hits = chat_mod.retrieve(question, state, top_k=top_k)
            _, stream = chat_mod.stream_answer(question, state)
        with st.expander(f"📎 {len(hits)} nguồn đã retrieve (state={state})"):
            for idx, hit in enumerate(hits, start=1):
                st.markdown(
                    f"**[{idx}]** {hit.title[:90]}  \n"
                    f"`paper_id={hit.paper_id}` · "
                    f"`score={hit.score:.4f}`"
                )
        response_text = st.write_stream(stream)
    st.session_state.messages.append(
        {"role": "assistant", "content": response_text, "hits": hits}
    )


PAGES = {
    "🏠 Overview": _overview_page,
    "📚 Paper Explorer": _explorer_page,
    "📊 Quality Dashboard": None,
    "🔀 State Compare": None,
    "💬 Ask the Corpus": _chat_page,
    "🏛 Kiến trúc": _architecture_page,
}


def main() -> None:
    st.set_page_config(**PAGE_CONFIG)

    page = st.sidebar.radio("📍 Điều hướng", list(PAGES.keys()))
    if page == "📊 Quality Dashboard":
        from app.dashboard import render as dashboard_render

        dashboard_render()
    elif page == "🔀 State Compare":
        from app.compare import render as compare_render

        compare_render()
    else:
        PAGES[page]()

    st.sidebar.divider()
    st.sidebar.caption("© 2026 Hniv · Pipeline + UI không sửa `src/`")


if __name__ == "__main__":
    main()
