import os
import streamlit as st
from slugify import slugify
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Set up SOP directory
SOP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sops")
os.makedirs(SOP_DIR, exist_ok=True)

# Function to handle new case submission UI
def show_add_case_form(db):
    st.subheader("📥 Submit a New SOP Case")

    # Cancel button to exit form (with a unique key)
    if st.button("❌ Cancel / Return to Main Screen", key="cancel_button"):
        st.session_state["show_add_case"] = False
        st.experimental_rerun()
        return

    # Begin the form block
    #with st.form(key="add_case_form"):
    with st.form("add_case_form"):
        summary = st.text_input("📌 Summary of the issue", value=st.session_state.get("summary", ""))

        filename_input = st.text_input(
            "📄 Filename (required)",
            value=st.session_state.get("filename_input", ""),
        )

        resolution = st.text_area("🛠️ Resolution steps", value=st.session_state.get("resolution", ""))
        related = st.text_input("🔗 Related SOPs (comma-separated, optional)", value=st.session_state.get("related", ""))

        submitted = st.form_submit_button("✅ Submit Case")

        if submitted:
            # Store back into session_state
            st.session_state.summary = summary
            st.session_state.filename_input = filename_input
            st.session_state.resolution = resolution
            st.session_state.related = related

            # if not summary:
            #     st.warning("⚠️ Summary is required.")
            #     return


            # Prepare the filename and path
            filename = filename_input.strip() or slugify(summary)
            filepath = os.path.join(SOP_DIR, f"{filename}.txt")

            # Check if file already exists
            if os.path.exists(filepath):
                st.warning(f"⚠️ File '{filename}.txt' already exists.")
                return

            # Create the content to save to the file
            content = f"Summary:\n{summary}\n\nResolution:\n{resolution}"
            if related:
                content += f"\n\nRelated SOPs: {related}"

            # Try saving the case to the file
            try:
                with open(filepath, 'w') as f:
                    f.write(content)
                st.success(f"✅ Case saved to: {filepath}")

                # Add to vector DB (optional, if `db` is provided)
                doc = Document(page_content=content, metadata={"source": filepath})
                splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=100)
                db.add_documents(splitter.split_documents([doc]))
                st.success("✅ Document added to the vector DB.")

                # Hide form after submission
                st.session_state["show_add_case"] = False
                st.rerun()

                # Optionally, reset the session state fields to clear the form
                st.session_state.summary = ""
                st.session_state.filename_input = ""
                st.session_state.resolution = ""
                st.session_state.related = ""

            except Exception as e:
                st.error(f"❌ Could not save file: {e}")

# Example of how to trigger the form (outside of the function)
if "show_add_case" not in st.session_state:
    st.session_state["show_add_case"] = False

if st.button("➕ Add New Case", key="add_new_case_button"):
    st.session_state["show_add_case"] = True

if st.session_state["show_add_case"]:
    show_add_case_form(db)
