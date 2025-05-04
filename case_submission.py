import os
from slugify import slugify
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Directory where new SOP case files are stored
SOP_DIR = "./sops"

# Reuse same splitter settings as main RAG logic
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

def add_single_file_to_db(filepath, db):
    """Reads a new file, splits it, and adds it to the existing vector DB."""
    with open(filepath, 'r') as f:
        content = f.read()

    doc = Document(page_content=content, metadata={"source": filepath})
    chunks = splitter.split_documents([doc])
    db.add_documents(chunks)
    print(f"✅ New document embedded and added to vector DB: {filepath}")

def handle_new_case_submission(db):
    """Collect a new case, save it as a .txt file, and add it to the live vector DB."""
    print("\n🆕 You are adding a new issue/solution to the assistant.")

    # Step 1: Get Summary first
    summary = input("📌 Enter a short summary of the issue: ").strip()
    if not summary:
        print("⚠️ Summary is required. Aborting.")
        return

    # Step 2: Suggest filename based on Summary
    suggested_name = slugify(summary)
    print(f"💡 Suggested file name: {suggested_name}.txt")
    filename = input("✏️ Enter a file name (or press Enter to accept suggestion): ").strip()
    if not filename:
        filename = suggested_name

    filepath = os.path.join(SOP_DIR, f"{filename}.txt")
    if os.path.exists(filepath):
        print(f"⚠️ File '{filepath}' already exists. Please choose a different name.")
        return

    # Step 3: Collect Resolution Procedure
    print("\n🛠️ Enter the resolution steps (you can write multiple lines; type 'END' to finish):")
    resolution_lines = []
    while True:
        line = input()
        if line.strip().lower() == 'end':
            break
        resolution_lines.append(line)
    resolution = "\n".join(resolution_lines).strip()

    # Step 4: Collect Related SOPs (optional)
    related_input = input("\n🔗 Enter related SOP name(s) (comma-separated, optional): ").strip()
    related_sops = [s.strip() for s in related_input.split(",") if s.strip()]

    # Step 5: Combine content and write to file
    content_lines = [
        f"Summary:\n{summary}",
        f"\nResolution:\n{resolution}"
    ]
    if related_sops:
        content_lines.append(f"\nRelated SOPs: {', '.join(related_sops)}")

    try:
        with open(filepath, 'w') as f:
            f.write("\n".join(content_lines))
        print(f"\n📁 Case saved to: {filepath}")
    except Exception as e:
        print(f"❌ Failed to write file: {e}")
        return

    # Step 6: Add document to live vector DB
