import os
from typing import List, Dict
from langchain_community.document_loaders import DirectoryLoader, TextLoader


def load_sop_files_from_config(internal_paths: Dict[str, str]):
    """
    Load SOP documents from multiple internal sources (defined in config.yaml).
    Args:
        internal_paths: dict { source_name: local_path }
    Returns:
        List of Document objects
    """
    all_docs = []

    for source_name, directory in internal_paths.items():
        if not os.path.exists(directory):
            print(f"⚠️  Directory does not exist yet: {directory} (skipping)")
            continue

        print(f"📁 Loading SOPs from: {directory} [{source_name}]")

        loader = DirectoryLoader(
            path=directory,
            glob="**/*",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
            show_progress=True
        )

        docs = loader.load()

        # Filter by allowed extensions
        allowed_exts = ('.md', '.asciidoc', '.txt')
        filtered_docs = [
            doc for doc in docs
            if doc.metadata["source"].lower().endswith(allowed_exts)
        ]

        # Tag with metadata (source type = repo name or local folder)
        for doc in filtered_docs:
            doc.metadata["source_type"] = source_name

        print(f"✅ Loaded {len(filtered_docs)} docs from '{source_name}'")

        all_docs.extend(filtered_docs)

    print(f"📦 Total documents loaded: {len(all_docs)}")
    return all_docs


def load_single_sop_folder(directory: str, source_name: str = "manual") -> List:
    """
    Load all SOP files from one folder (utility function).
    Can be used for 'my' or 'new' folders separately.
    """
    if not os.path.exists(directory):
        print(f"📁 Creating missing directory: {directory}")
        os.makedirs(directory, exist_ok=True)

    loader = DirectoryLoader(
        path=directory,
        glob="**/*",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=False
    )

    docs = loader.load()
    allowed_exts = ('.md', '.asciidoc', '.txt')
    filtered_docs = [
        doc for doc in docs
        if doc.metadata["source"].lower().endswith(allowed_exts)
    ]

    for doc in filtered_docs:
        doc.metadata["source_type"] = source_name

    return filtered_docs
