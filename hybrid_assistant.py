# hybrid_assistant.py
import requests
from urllib.parse import quote_plus
import trafilatura
from langchain.chains import RetrievalQA
from langchain_community.vectorstores import FAISS

from engines.base import BaseEngine
from engines.ollama_engine import OllamaEngine
from engines.gemini_engine import GeminiEngine
from engines.serpapi_engine import SerpAPIEngine


class ExternalWebRetriever:
    """Retrieve and clean text from public web pages."""

    def fetch_text(self, url: str) -> str | None:
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            text = trafilatura.extract(resp.text)
            return text if text else None
        except Exception as e:
            print(f"⚠ Web retrieval failed for {url}: {e}")
            return None


class HybridSOPAssistant:
    """
    SOP Assistant supporting three modes:
    1. RAG (internal SOPs only)
    2. Hybrid (internal SOPs + external web)
    3. External (external web only)
    """

    def __init__(self, db: FAISS, engines_config: dict, mode: str = "rag"):
        self.db = db
        self.retriever = db.as_retriever(search_kwargs={"k": 10})
        self.web_retriever = ExternalWebRetriever()
        self.mode = mode.lower()
        self.engines_config = engines_config

        # Initialize engine instances
        self.engine_instances: dict[str, BaseEngine] = {}
        self.current_engine: BaseEngine = None
        self._init_engines()

        # Setup QA with default LLM engine (Ollama)
        default_llm_engine = (
            self.current_engine
            if isinstance(self.current_engine, OllamaEngine)
            else OllamaEngine(name="default_ollama")
        )
        self.qa = RetrievalQA.from_chain_type(
            llm=default_llm_engine.llm,
            retriever=self.retriever,
            return_source_documents=True
        )

        # Collect AWS doc URLs
        self.aws_doc_urls = []
        for src in engines_config.get("external_sources", []):
            aws_urls = src.get("aws_docs", [])
            if aws_urls:
                self.aws_doc_urls.extend(aws_urls)

    def _init_engines(self):
        """Initialize external engines from config."""
        for src in self.engines_config.get("external_sources", []):
            name = src.get("name")
            engine_type = src.get("engine")
            api_key = src.get("api_key", None)

            if engine_type == "ollama":
                self.engine_instances[name] = OllamaEngine(name=name)
            elif engine_type == "gemini":
                self.engine_instances[name] = GeminiEngine(api_key)
            elif engine_type == "serpapi":
                self.engine_instances[name] = SerpAPIEngine(api_key)

        # Set default engine
        if self.engine_instances:
            self.current_engine = next(iter(self.engine_instances.values()))
        else:
            self.current_engine = OllamaEngine(name="default_ollama")

    def set_engine(self, name: str):
        if name not in self.engine_instances:
            raise ValueError(f"Engine '{name}' not found")
        self.current_engine = self.engine_instances[name]
        print(f"⚙️ Switched engine to: {name}")

    def set_mode(self, mode: str):
        if mode.lower() not in ("rag", "hybrid", "external"):
            raise ValueError("Mode must be one of: RAG, Hybrid, External")
        self.mode = mode.lower()
        print(f"⚙️ Switched mode to: {self.mode}")

    def query(self, user_query: str) -> dict:
        result_text = ""
        sources = []

        seen_sources = set()  # Keep track of added sources to avoid duplicates

        # --- Internal RAG search ---
        if self.mode in ("rag", "hybrid"):
            qa_result = self.qa.invoke({"query": user_query})
            result_text += qa_result["result"]

            for doc in qa_result["source_documents"]:
                src_path = doc.metadata.get("source")
                if src_path not in seen_sources:
                    sources.append({"source": src_path, "type": "internal"})
                    seen_sources.add(src_path)

        # --- External / Hybrid search ---
        if self.mode in ("hybrid", "external"):
            web_texts = self._fetch_external_texts(user_query)
            for wt in web_texts:
                url = wt["url"]
                if url not in seen_sources:
                    sources.append({"source": url, "type": "external"})
                    seen_sources.add(url)

            if web_texts:
                combined_text = "\n\n".join(wt["text"] for wt in web_texts)
                result_text += "\n\n" + self.current_engine.invoke(combined_text)

        return {"result": result_text, "sources": sources}


    def _fetch_external_texts(self, query: str) -> list[dict[str, str]]:
        results = []

        # --- AWS docs ---
        for url in self.aws_doc_urls:
            text = self.web_retriever.fetch_text(url)
            if text:
                results.append({"url": url, "text": text})

        # --- Other configured engines ---
        for src in self.engines_config.get("external_sources", []):
            engine_name = src.get("name")
            urls = src.get("urls", [])

            # Fetch URLs for this engine
            for url in urls:
                text = self.web_retriever.fetch_text(url)
                if text:
                    results.append({"url": url, "text": text})

            # If no URLs, maybe generate dynamic search URLs depending on engine
            if not urls:
                if engine_name.lower() == "general-search":
                    wiki_url = f"https://en.wikipedia.org/wiki/{quote_plus(query).replace('+','_')}"
                    so_url = f"https://stackoverflow.com/search?q={quote_plus(query)}"
                    for url in [wiki_url, so_url]:
                        text = self.web_retriever.fetch_text(url)
                        if text:
                            results.append({"url": url, "text": text})

        return results
