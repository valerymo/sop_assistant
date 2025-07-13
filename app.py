import streamlit as st
from utils.loaders import load_sop_files
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain_ollama import OllamaLLM
from case_submission_ui import show_add_case_form

# Initialize once
@st.cache_resource
def setup_qa_system():
    docs = load_sop_files("./sops")
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
    chunks = splitter.split_documents(docs)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma.from_documents(chunks, embeddings)
    retriever = db.as_retriever()
    llm = OllamaLLM(model="mistral")
    qa = RetrievalQA.from_chain_type(llm=llm, retriever=retriever, return_source_documents=True)
    return qa, db

qa, db = setup_qa_system()

st.title("📄 SOP Assistant")
st.write("Ask any question related to the SOPs, or add a new case.")

query = st.text_input("Enter your question:")

if st.button("Ask"):
    if query:
        result = qa.invoke({"query": query})
        st.subheader("🤖 Assistant Response:")
        st.write(result["result"])

        st.subheader("📎 Source Documents:")
        for doc in result["source_documents"]:
            st.markdown(f"- `{doc.metadata.get('source')}`")

# if st.button("➕ Add New Case"):
#show_add_case_form(db)

if st.button("➕ Add New Case"):
    st.session_state["show_add_case"] = True

if st.session_state.get("show_add_case", False):
    show_add_case_form(db)

