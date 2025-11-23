# app.py
import os
import streamlit as st
from utils.loaders import load_sop_files_from_config
from utils.config_loader import load_config, setup_internal_sources
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from hybrid_assistant import HybridSOPAssistant
from case_submission_ui import show_add_case_form

# ------------------------------
# Load configuration & SOPs
# ------------------------------
config = load_config("config.yaml")
internal_sources = config.get("internal_sources", [])
local_paths = setup_internal_sources(internal_sources)

st.title("📄 SOP Assistant")

st.write("Ask a question related to the SOPs, switch modes, or add a new case.")

docs = load_sop_files_from_config(local_paths)
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
chunks = splitter.split_documents(docs)
embeddings = FastEmbedEmbeddings()
db = FAISS.from_documents(chunks, embeddings)

# ------------------------------
# Initialize Assistant
# ------------------------------
assistant = HybridSOPAssistant(db=db, engines_config=config)

# ------------------------------
# UI: Mode selection
# ------------------------------
mode_options = ["rag", "hybrid", "external"]
if "current_mode" not in st.session_state:
    st.session_state.current_mode = assistant.mode

new_mode = st.selectbox("Select mode", mode_options, index=mode_options.index(st.session_state.current_mode))
if new_mode != st.session_state.current_mode:
    assistant.set_mode(new_mode)
    st.session_state.current_mode = new_mode
    st.success(f"Mode switched to {new_mode.upper()}")

# ------------------------------
# UI: Engine selection
# ------------------------------
engine_options = list(assistant.engine_instances.keys())
if engine_options:
    if "current_engine" not in st.session_state:
        st.session_state.current_engine = assistant.current_engine or engine_options[0]

    new_engine = st.selectbox("Select external engine", engine_options, index=engine_options.index(st.session_state.current_engine))
    if new_engine != st.session_state.current_engine:
        assistant.set_engine(new_engine)
        st.session_state.current_engine = new_engine
        st.success(f"External engine switched to {new_engine}")

# ------------------------------
# UI: Query input
# ------------------------------
query = st.text_input("Enter your question:")

if st.button("Ask"):
    if query:
        try:
            result = assistant.query(query)
            st.subheader("🤖 Assistant Response:")
            st.write(result.get("result", ""))

            st.subheader("📎 Sources:")
            for doc in result.get("sources", []):
                if isinstance(doc, dict):
                    st.markdown(f"- [{doc.get('type')}] `{doc.get('source')}`")
                else:
                    st.markdown(f"- {doc}")

        except Exception as e:
            st.error(f"⚠ Error during query: {e}")

# ------------------------------
# UI: Add new SOP case
# ------------------------------
if "show_add_case" not in st.session_state:
    st.session_state["show_add_case"] = False

if st.button("➕ Add New Case"):
    st.session_state["show_add_case"] = True

if st.session_state["show_add_case"]:
    show_add_case_form(db)
