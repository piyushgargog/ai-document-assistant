"""Streamlit UI for the AI Document Assistant."""

import streamlit as st
from dotenv import load_dotenv

import pipeline
from llm_client import LLMConfigError, LLMRequestError

load_dotenv()

st.set_page_config(page_title="AI Document Assistant", page_icon="\U0001F4C4", layout="centered")

if "messages" not in st.session_state:
    st.session_state["messages"] = []
if "_index_state" not in st.session_state:
    st.session_state["_index_state"] = None
if "_cache_key" not in st.session_state:
    st.session_state["_cache_key"] = None
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = 0

st.title("AI Document Assistant")
st.caption(
    "Upload a PDF and ask questions about it in plain language. Answers are "
    "grounded strictly in the document's content, with the source page shown "
    "for every answer."
)


def render_sources(sources: list[dict]) -> None:
    """Render a per-answer sources popover: page, similarity score, passage.

    Passage text is rendered with st.text, not markdown: it is untrusted
    document content and must not be able to inject formatting.
    """
    with st.popover(f"\U0001F4C4 Sources ({len(sources)})"):
        for i, src in enumerate(sources, start=1):
            st.markdown(f"**Page {src['page']}**")
            st.caption(f"similarity: {src['score']:.3f}")
            st.text(src["text"], width="stretch")
            if i < len(sources):
                st.divider()


# --- Sidebar: file upload + document status + advanced settings ---
with st.sidebar:
    st.header("Document")
    uploaded_file = st.file_uploader(
        "Upload a PDF", type=["pdf"], key=f"uploader_{st.session_state['uploader_key']}"
    )

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
    if st.session_state["_cache_key"] != cache_key:
        with st.status("Reading and indexing document...", expanded=False) as status:
            index_state = pipeline.ingest(uploaded_file.getvalue(), chunk_size, chunk_overlap)
            if index_state is None:
                status.update(label="Could not read this document", state="error")
            else:
                status.update(label="Document indexed", state="complete")

        st.session_state["_cache_key"] = cache_key
        st.session_state["_index_state"] = index_state
        st.session_state["messages"] = []
        if index_state is not None:
            st.session_state["messages"].append(
                {
                    "role": "assistant",
                    "content": "Document loaded — ask me anything about it.",
                    "sources": None,
                }
            )

    index_state = st.session_state["_index_state"]

    with st.sidebar:
        if index_state is None:
            st.error(
                "Couldn't extract any text from this PDF. It may be empty, "
                "image-only (scanned without OCR), password-protected, or "
                "corrupted."
            )
        else:
            with st.container(border=True):
                st.markdown(f"**{uploaded_file.name}**")
                st.caption(f"{index_state.num_pages} pages · {index_state.num_chunks} chunks")
                st.badge("Ready", color="green")

            if st.button("Remove document", width="stretch"):
                st.session_state["uploader_key"] += 1
                st.session_state["_index_state"] = None
                st.session_state["_cache_key"] = None
                st.session_state["messages"] = []
                st.rerun()

    if index_state is not None:
        for msg in st.session_state["messages"]:
            with st.chat_message(msg["role"]):
                if msg.get("is_error"):
                    st.error(msg["content"])
                else:
                    st.write(msg["content"])
                if msg.get("sources"):
                    render_sources(msg["sources"])

        question = st.chat_input("Ask a question about the document...", max_chars=1000)
        if question:
            st.session_state["messages"].append({"role": "user", "content": question, "sources": None})
            with st.chat_message("user"):
                st.write(question)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        result = pipeline.answer(question, index_state, top_k=top_k)
                        answer_text, sources, is_error = result["answer"], result["sources"], False
                    except LLMConfigError as e:
                        answer_text, sources, is_error = str(e), None, True
                    except LLMRequestError as e:
                        answer_text, sources, is_error = f"The LLM API request failed: {e}", None, True

                if is_error:
                    st.error(answer_text)
                else:
                    st.write(answer_text)
                    if sources:
                        render_sources(sources)

            st.session_state["messages"].append(
                {
                    "role": "assistant",
                    "content": answer_text,
                    "sources": sources,
                    "is_error": is_error,
                }
            )
else:
    st.session_state["_index_state"] = None
    st.session_state["_cache_key"] = None

    with st.container(border=True):
        st.markdown("#### Get started")
        st.write(
            "Upload a PDF in the sidebar to begin. Once it's indexed, ask "
            "questions here and see exactly which page each answer came from."
        )
