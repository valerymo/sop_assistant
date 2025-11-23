# main.py
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS

from utils.config_loader import load_config, setup_internal_sources
from utils.loaders import load_sop_files_from_config
from case_submission import handle_new_case_submission_cli
from hybrid_assistant import HybridSOPAssistant

# ------------------------------
# Load configuration & SOPs
# ------------------------------
config = load_config("config.yaml")
internal_sources = config.get("internal_sources", [])
local_paths = setup_internal_sources(internal_sources)

print("📂 Loading SOP documents...")
docs = load_sop_files_from_config(local_paths)
if not docs:
    print("⚠️ No SOP documents loaded. Make sure your internal sources exist.")
    exit(1)
print(f"✅ {len(docs)} documents loaded from internal sources.")

# ------------------------------
# Split documents & create FAISS DB
# ------------------------------
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
chunks = splitter.split_documents(docs)

print("🧠 Creating vector database...")
embeddings = FastEmbedEmbeddings()
db = FAISS.from_documents(chunks, embeddings)

# ------------------------------
# Initialize Assistant
# ------------------------------
assistant = HybridSOPAssistant(db=db, engines_config=config)

# ------------------------------
# Chat loop
# ------------------------------
print("🤖 SOP Assistant ready. Type your question below.")
print("   Type 'add case' to add a new issue/solution.")
print("   Type 'mode' to switch between RAG / Hybrid / External.")
print("   Type 'engine' to switch external engine (Gemini / SerpAPI / Ollama).")
print("   Type 'help' for commands.")
print("   Type 'exit' to quit.")

while True:
    user_input = input("\n📝 You: ").strip()
    if not user_input:
        continue
    cmd = user_input.lower()

    if cmd in ("exit", "quit"):
        print("👋 Bye! Take care.")
        break

    if cmd in ("help", "-help"):
        print("🤖 Commands:")
        print("   - Type your question to get an answer")
        print("   - 'add case' to add a new issue/solution")
        print("   - 'mode' to switch between RAG / Hybrid / External")
        print("   - 'engine' to switch external engine")
        print("   - 'exit' to quit")
        continue

    if cmd == "add case":
        handle_new_case_submission_cli(db)
        continue

    if cmd == "mode":
        while True:
            new_mode = input("Enter mode (RAG / Hybrid / External): ").strip()
            if not new_mode:
                print("⚠ Mode cannot be empty.")
                continue
            try:
                assistant.set_mode(new_mode)

                # --- External mode URL choice ---
                if new_mode.lower() == "external":
                    answer = input("Do you want to include configured URLs in the search? [yes]/no: ").strip().lower()
                    assistant.use_config_urls = (answer != "no")

                break
            except ValueError as e:
                print(f"⚠ {e}")
        continue

    if cmd == "engine":
        engine_names = list(assistant.engine_instances.keys())
        if not engine_names:
            print("⚠ No external engines configured.")
            continue
        print("Available engines:", ", ".join(engine_names))
        new_engine = input("Enter engine name: ").strip()
        if new_engine:
            try:
                assistant.set_engine(new_engine)
            except ValueError as e:
                print(f"⚠ {e}")
        continue

    # Query the assistant
    try:
        result = assistant.query(user_input)
    except Exception as e:
        print(f"⚠ Error during query: {e}")
        continue

    print("\n🤖 Assistant:\n", result.get("result", ""))
    sources = result.get("sources", [])
    if sources:
        print("\n📎 Sources:")
        for src in sources:
            if isinstance(src, dict):
                s_type = src.get("type", "unknown")
                s_path = src.get("source", "")
                print(f" - [{s_type}] {s_path}")
            else:
                print(f" - {src}")
