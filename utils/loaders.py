from langchain_community.document_loaders import DirectoryLoader, TextLoader


def load_sop_files(directory: str):
    loader = DirectoryLoader(
        path=directory,
        glob="**/*",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True
    )

    all_docs = loader.load()

    # Filter by allowed extensions
    allowed_exts = ('.md', '.asciidoc', '.txt')
    filtered_docs = [
        doc for doc in all_docs
        if doc.metadata['source'].lower().endswith(allowed_exts)
    ]
    return filtered_docs
