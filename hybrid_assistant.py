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
    3. External (external web only, dynamic search + optional config URLs)
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

        # Setup QA with default LLM (internal RAG)
        default_llm_engine = self.engine_instances.get("ollama") or OllamaEngine(name="default_ollama")
        self.qa = RetrievalQA.from_chain_type(
            llm=default_llm_engine.llm,
            retriever=self.retriever,
            return_source_documents=True
        )

        # Collect AWS/GCP doc URLs from config
        self.external_config_urls: list[str] = []
        for src in engines_config.get("external_sources", []):
            urls = src.get("urls") or []
            self.external_config_urls.extend(urls)

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
            # fallback
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

        # --- Internal RAG search ---
        if self.mode in ("rag", "hybrid"):
            qa_result = self.qa.invoke({"query": user_query})
            result_text += qa_result["result"]
            sources.extend(
                {"source": doc.metadata.get("source"), "type": "internal"}
                for doc in qa_result["source_documents"]
            )

        # --- External / Hybrid search ---
        if self.mode in ("hybrid", "external"):
            web_texts = self._fetch_external_texts(user_query, external_only=self.mode=="external")
            if web_texts:
                for wt in web_texts:
                    sources.append({"source": wt["url"], "type": "external"})

                combined_text = "\n\n".join(wt["text"] for wt in web_texts)
                if self.mode == "external" or web_texts:
                    result_text += "\n\n" + self.current_engine.invoke(combined_text)

        # Deduplicate sources
        seen = set()
        cleaned_sources = []
        for s in sources:
            key = f"{s['type']}|{s['source']}"
            if key not in seen:
                cleaned_sources.append(s)
                seen.add(key)
        sources = cleaned_sources

        return {"result": result_text, "sources": sources}

    def _fetch_external_texts(self, query: str, external_only: bool = False) -> list[dict]:
        """
        Fetch text from external sources:
        - If external_only=True: ignore internal URLs, only dynamic search
        - Else: use config URLs + dynamic search
        """
        results = []

        # Use config URLs unless in pure external mode
        if not external_only and self.external_config_urls:
            for url in self.external_config_urls:
                text = self.web_retriever.fetch_text(url)
                if text:
                    results.append({"url": url, "text": text})

        # Dynamic search URLs (Wikipedia, StackOverflow, AWS/GCP docs)
        dynamic_urls = [
            f"https://en.wikipedia.org/wiki/{quote_plus(query).replace('+','_')}",
            f"https://stackoverflow.com/search?q={quote_plus(query)}"
        ]
        # Add more dynamic doc URLs if needed, e.g., AWS/GCP RDS or Redis docs
        for url in dynamic_urls:
            text = self.web_retriever.fetch_text(url)
            if text:
                results.append({"url": url, "text": text})

        return results
