# hybrid_assistant.py
import requests
from langchain.chains import RetrievalQA
from langchain_ollama import OllamaLLM
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import FastEmbedEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import trafilatura
from urllib.parse import quote_plus


class ExternalWebRetriever:
    """Retrieve and clean text from public web pages."""

    def fetch_text(self, url: str) -> str | None:
        try:
            # FIX 1: Add real browser user-agent → Wikipedia no longer blocks (403 gone)
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36"
                )
            }

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            text = trafilatura.extract(response.text)
            return text if text else None

        except Exception as e:
            print(f"⚠ Web retrieval failed for {url}: {e}")
            return None


class HybridSOPAssistant:
    """
    SOP Assistant with three modes:
    1. RAG only (internal SOPs + local LLM)
    2. Hybrid (internal SOPs + web search + local LLM)
    3. External (web search only + local LLM)
    """

    def __init__(
        self,
        db: FAISS,
        model_name: str = "mistral",
        mode: str = "RAG",
        aws_doc_urls: list[str] | None = None,
    ):
        self.db = db
        self.llm = OllamaLLM(model=model_name)
        self.retriever = db.as_retriever(search_kwargs={"k": 10})
        self.qa = RetrievalQA.from_chain_type(
            llm=self.llm,
            retriever=self.retriever,
            return_source_documents=True
        )
        self.web_retriever = ExternalWebRetriever()
        self.mode = mode.lower()
        self.aws_doc_urls = aws_doc_urls or []

    def set_mode(self, mode: str):
        mode = mode.lower()
        if mode not in ("rag", "hybrid", "external"):
            raise ValueError("Mode must be one of: RAG, Hybrid, External")
        self.mode = mode
        print(f"⚙️ Switched mode to: {self.mode}")

    def query(self, user_query: str) -> dict:
        result_text = ""
        sources = []

        # ---------- INTERNAL SOP SEARCH ----------
        if self.mode in ("rag", "hybrid"):
            qa_result = self.qa.invoke({"query": user_query})
            result_text += qa_result["result"]

            sources.extend([
                {"source": doc.metadata.get("source"), "type": "internal"}
                for doc in qa_result["source_documents"]
            ])

            # Deduplicate internal sources
            seen_internal = set()
            cleaned_sources = []
            for entry in sources:
                if entry["type"] == "internal":
                    if entry["source"] not in seen_internal:
                        cleaned_sources.append(entry)
                        seen_internal.add(entry["source"])
                else:
                    cleaned_sources.append(entry)
            sources = cleaned_sources

        # ---------- EXTERNAL / HYBRID SEARCH ----------
        if self.mode in ("hybrid", "external"):
            web_texts = self._web_search(user_query)

            if web_texts:
                combined_text = ""

                for wt in web_texts:
                    combined_text += wt["text"] + "\n\n"
                    sources.append({"source": wt["url"], "type": "external"})

                    if self.mode == "hybrid":
                        snippet = wt["text"][:500]
                        result_text += f"\n\n[Web info]: {snippet}..."

                if self.mode == "external" and combined_text.strip():
                    result_text = self.llm.invoke(combined_text)

            else:
                if self.mode == "external":
                    result_text = "⚠ No usable text found from external sources."

        return {"result": result_text, "sources": sources}

    def _web_search(self, query: str) -> list[dict]:
        results = []

        # ---------- AWS DOCS ----------
        for url in self.aws_doc_urls:
            text = self.web_retriever.fetch_text(url)
            if text:
                results.append({"url": url, "text": text})

        # ---------- FIX 2: Wikipedia URL format corrected ----------
        wiki_url = f"https://en.wikipedia.org/wiki/{quote_plus(query).replace('+', '_')}"

        search_sites = [
            wiki_url,
            f"https://stackoverflow.com/search?q={quote_plus(query)}"
        ]

        # Fetch from sites
        for url in search_sites:
            text = self.web_retriever.fetch_text(url)
            if text:
                results.append({"url": url, "text": text})

        return results
