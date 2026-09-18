"""Streamlit UI for the AI Document Assistant."""

import streamlit as st
from dotenv import load_dotenv

import pipeline
from llm_client import LLMConfigError, LLMRequestError

load_dotenv()

st.set_page_config(page_title="AI Document Assistant", page_icon="\U0001F4C4")
st.title("AI Document Assistant")
st.caption(
    "Upload a PDF and ask questions about it in plain language. Answers are "
    "grounded strictly in the document's content, with the source page shown "
    "for every answer."
)

# --- Sidebar: file upload + advanced settings (collapsed by default) ---
with st.sidebar:
    st.header("Document")
    uploaded_file = st.file_uploader("Upload a PDF", type=["pdf"])

    with st.expander("Advanced settings", expanded=False):
        chunk_size = st.slider("Chunk size (characters)", 200, 2000, pipeline.DEFAULT_CHUNK_SIZE, step=100)
        chunk_overlap = st.slider("Chunk overlap (characters)", 0, 500, pipeline.DEFAULT_CHUNK_OVERLAP, step=50)
        top_k = st.slider("Passages to retrieve (top-k)", 1, 10, pipeline.DEFAULT_TOP_K)

if chunk_overlap >= chunk_size:
    st.sidebar.error("Chunk overlap must be smaller than chunk size.")
    st.stop()

# --- Ingest on upload (or settings change) ---
if uploaded_file is not None:
    cache_key = (uploaded_file.name, uploaded_file.size, chunk_size, chunk_overlap)
    if st.session_state.get("_cache_key") != cache_key:
        with st.spinner("Processing document..."):
            index_state = pipeline.ingest(uploaded_file.getvalue(), chunk_size, chunk_overlap)
        st.session_state["_cache_key"] = cache_key
        st.session_state["_index_state"] = index_state

    index_state = st.session_state.get("_index_state")

    if index_state is None:
        st.error(
            "Couldn't extract any text from this PDF. It may be empty, "
            "image-only (scanned without OCR), or corrupted."
        )
    else:
        st.success(f"Document ready: {index_state.num_pages} pages, {index_state.num_chunks} chunks indexed.")

        question = st.text_input("Ask a question about the document")
        if question:
            with st.spinner("Retrieving passages and generating answer..."):
                try:
                    result = pipeline.answer(question, index_state, top_k=top_k)
                except LLMConfigError as e:
                    st.error(str(e))
                    result = None
                except LLMRequestError as e:
                    st.error(f"The LLM API request failed: {e}")
                    result = None

            if result is not None:
                st.markdown("### Answer")
                st.write(result["answer"])

                with st.expander(f"Sources ({len(result['sources'])} passages used)"):
                    for i, src in enumerate(result["sources"], start=1):
                        st.markdown(f"**{i}. Page {src['page']}** — similarity: {src['score']:.3f}")
                        st.text(src["text"])
else:
    st.info("Upload a PDF in the sidebar to get started.")
