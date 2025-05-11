import os
from slugify import slugify
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
import streamlit as st
import logging

# Directory where new SOP case files are stored
# SOP_DIR = "./sops"
SOP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sops")

# Reuse same splitter settings as main RAG logic
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)

def add_single_file_to_db(filepath, db):
    """Reads a new file, splits it, and adds it to the existing vector DB."""
    with open(filepath, 'r') as f:
        content = f.read()

    doc = Document(page_content=content, metadata={"source": filepath})
    chunks = splitter.split_documents([doc])
    db.add_documents(chunks)
    st.success(f"✅ New document added to the vector DB: {filepath}")


def handle_new_case_submission_ui(db):
    logging.basicConfig(level=logging.DEBUG,  # Set logging level (DEBUG, INFO, etc.)
                        format="%(asctime)s - %(levelname)s - %(message)s")  # Log format

    logging.debug("Starting new case submission process")
    st.subheader("📥 Submit a New SOP Case")

    # Option to return to the main screen
    if st.button("❌ Cancel / Return to Main Screen"):
        st.session_state["show_add_case"] = False
        st.experimental_rerun()
        return  # Exit the function early if Cancel is pressed

    # Form for submitting new case
    with st.form("case_submission_form", clear_on_submit=True):
        summary = st.text_input("📌 Summary of the issue")
        suggested_name = slugify(summary) if summary else ""
        filename_input = st.text_input("✏️ Optional filename (blank = auto from summary)", value=suggested_name)
        resolution = st.text_area("🛠️ Resolution steps")
        related_input = st.text_input("🔗 Related SOPs (comma-separated, optional)")

        submitted = st.form_submit_button("✅ Submit")

        # Check if the form is submitted
        if submitted:
            # Ensure summary is not empty
            if not summary:
                st.warning("⚠️ Summary is required. Please enter a summary.")
                return  # Do not continue if summary is empty

            # Ensure filename is not empty
            if not filename_input:
                st.warning("⚠️ File name is required. Please enter a file name.")
                return  # Do not continue if file name is empty

            # Generate filename if not entered manually
            filename = filename_input.strip() or slugify(summary)
            filepath = os.path.join(SOP_DIR, f"{filename}.txt")

            # Prevent overwriting existing file
            if os.path.exists(filepath):
                st.warning(f"⚠️ File '{filename}.txt' already exists.")
                return

            # Collect related SOPs if any
            related_sops = [s.strip() for s in related_input.split(",") if s.strip()]

            # Create content lines for the new case file
            content_lines = [
                f"Summary:\n{summary}",
                f"\nResolution:\n{resolution}"
            ]
            if related_sops:
                content_lines.append(f"\nRelated SOPs: {', '.join(related_sops)}")

            try:
                # Save the new case to a file
                with open(filepath, "w") as f:
                    f.write("\n".join(content_lines))
                st.success(f"📁 Case saved to: {filepath}")
                add_single_file_to_db(filepath, db)
            except Exception as e:
                st.error(f"❌ Could not save file: {e}")
