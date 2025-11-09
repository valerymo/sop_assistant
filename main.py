import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_ollama import OllamaLLM

from case_submission import handle_new_case_submission_cli
from utils.config_loader import load_config, setup_internal_sources
from utils.loaders import load_sop_files_from_config

# --- Load configuration ---
config = load_config("config.yaml")

internal_sources = config.get("internal_sources", [])
local_paths = setup_internal_sources(internal_sources)


# --- Load and prepare SOP documents ---
print("📂 Loading SOP documents...")
docs = load_sop_files_from_config(local_paths)

if not docs:
    print("⚠️ No SOP documents loaded. Make sure your internal sources exist.")
    exit(1)
else:
    print(f"✅ {len(docs)} documents loaded from internal sources.")

# --- Split documents into chunks ---
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
chunks = splitter.split_documents(docs)

# --- Create vector database ---
print("🧠 Creating vector database...")
embeddings = FastEmbedEmbeddings()
db = FAISS.from_documents(chunks, embeddings)

# --- Setup RetrievalQA with LLM ---
retriever = db.as_retriever()
llm = OllamaLLM(model="mistral")
qa = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    return_source_documents=True
)

# --- Chat loop ---
print("🤖 SOP Assistant ready. Type your question below.")
print("   Type 'add case' to add a new issue/solution.")
print("   Type 'exit' to quit.")

while True:
    query = input("\n📝 You: ")
    if query.lower() in ("exit", "quit"):
        print("👋 Bye! Take care.")
        break

    if query.lower() == "add case":
        # Prompt to add a new case
        handle_new_case_submission_cli(db)
        continue  # Skip the rest of the loop

    # Run query through the RAG assistant
    result = qa.invoke({"query": query})

    print("\n🤖 Assistant:\n", result["result"])

    print("\n📎 Sources:")
    for doc in result["source_documents"]:
        source_type = doc.metadata.get("source_type", "unknown")
        print(f" - [{source_type}] {doc.metadata.get('source')}")
