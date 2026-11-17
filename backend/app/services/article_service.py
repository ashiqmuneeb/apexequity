import hashlib
import json
from pathlib import Path

from fastapi import HTTPException
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    VectorStoreIndex,
)
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.core.config import settings
from app.core.logger import logger
from app.schemas.article import ArticleItem
from app.services.rag_engine import rag_engine_service


class ArticleService:
    """Handles financial document corpus operations and vector indexing.

    Attaches ticker metadata, strips absolute paths, updates index on delete,
    and caches file hashes to avoid rebuilding unaffected documents.
    """

    def __init__(self):
        settings.ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
        settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def _compute_hashes(self) -> dict[str, str]:
        """Computes SHA256 hashes of all text and markdown files in the articles directory."""
        hashes = {}
        files = sorted(settings.ARTICLES_DIR.glob("*.txt")) + sorted(
            settings.ARTICLES_DIR.glob("*.md")
        )
        for f in files:
            try:
                content = f.read_bytes()
                hashes[f.name] = hashlib.sha256(content).hexdigest()
            except Exception as e:
                logger.warning(f"Could not hash {f.name}: {e}")
        return hashes

    def _load_stored_hashes(self) -> dict[str, str]:
        hash_file = settings.STORAGE_DIR / "file_hashes.json"
        if hash_file.exists():
            try:
                return json.loads(hash_file.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_stored_hashes(self, hashes: dict[str, str]) -> None:
        hash_file = settings.STORAGE_DIR / "file_hashes.json"
        try:
            hash_file.write_text(json.dumps(hashes, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning(f"Could not save file hashes: {e}")

    def list_articles(self) -> list[ArticleItem]:
        """Lists all corporate reports and articles in the corpus."""
        items: list[ArticleItem] = []
        files = sorted(settings.ARTICLES_DIR.glob("*.txt")) + sorted(
            settings.ARTICLES_DIR.glob("*.md")
        )
        for file in files:
            try:
                content = file.read_text(encoding="utf-8")
                ticker = file.stem.upper()
                preview = content[:160] + "..." if len(content) > 160 else content
                items.append(
                    ArticleItem(
                        filename=file.name,
                        ticker=ticker,
                        length=len(content),
                        preview=preview,
                        content=content,
                    )
                )
            except Exception as e:
                logger.warning(f"Error reading article {file.name}: {e}")
        return items

    def save_article(self, ticker: str, content: str) -> str:
        """Saves or updates a stock article file and updates vector storage."""
        clean_ticker = ticker.strip().upper().replace(" ", "_")
        if not clean_ticker:
            raise HTTPException(
                status_code=400, detail="Stock ticker symbol is required."
            )

        file_path = settings.ARTICLES_DIR / f"{clean_ticker}.txt"
        file_path.write_text(content.strip(), encoding="utf-8")
        logger.info(f"Article saved for ticker: {clean_ticker}")

        # Automatically synchronize index
        self.build_and_persist_index()
        return f"{clean_ticker}.txt"

    def delete_article(self, ticker: str) -> None:
        """Deletes an article file for a given ticker and re-indexes storage."""
        clean_ticker = ticker.strip().upper()
        file_path = settings.ARTICLES_DIR / f"{clean_ticker}.txt"
        if not file_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Article for {clean_ticker} not found."
            )

        file_path.unlink()
        logger.info(f"Article file deleted for ticker: {clean_ticker}")

        # Re-index to ensure deleted document nodes are purged from vector store
        self.build_and_persist_index(force_rebuild=True)
        rag_engine_service.invalidate_cache()
        logger.info(f"Vector storage re-indexed after deleting {clean_ticker}")

    def fetch_live_stock_data(self, ticker: str) -> dict:
        """Fetches real-time financial statements and company profile from Yahoo Finance,

        saves to ./articles, and synchronizes the vector index.
        """
        clean_ticker = ticker.strip().upper().replace(" ", "")
        if not clean_ticker:
            raise HTTPException(status_code=400, detail="Stock ticker is required.")

        try:
            import yfinance as yf

            logger.info(f"Querying Yahoo Finance for ticker: {clean_ticker}")
            stock = yf.Ticker(clean_ticker)
            info = stock.info

            if not info or not info.get("shortName"):
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"Could not find financial market data for ticker symbol '{clean_ticker}'."
                    ),
                )

            name = info.get("longName") or info.get("shortName")
            sector = info.get("sector", "Unknown Sector")
            industry = info.get("industry", "Unknown Industry")
            market_cap = info.get("marketCap")
            cap_str = f"${market_cap / 1e9:.2f} Billion" if market_cap else "N/A"

            rev = info.get("totalRevenue")
            rev_str = f"${rev / 1e9:.2f} Billion" if rev else "N/A"

            growth = info.get("revenueGrowth")
            growth_str = f"{growth * 100:+.1f}%" if growth is not None else "N/A"

            gm = info.get("grossMargins")
            gm_str = f"{gm * 100:.1f}%" if gm is not None else "N/A"

            om = info.get("operatingMargins")
            om_str = f"{om * 100:.1f}%" if om is not None else "N/A"

            pe = info.get("forwardPE")
            pe_str = f"{pe:.1f}" if pe else "N/A"

            summary = info.get(
                "longBusinessSummary", "No corporate summary available."
            )

            # Compile into a structured corporate overview document
            content = (
                f"{name} ({clean_ticker}) Financial & Corporate Overview\n\n"
                f"Sector: {sector} | Industry: {industry}\n"
                f"Market Capitalization: {cap_str} | Forward P/E Ratio: {pe_str}\n\n"
                f"Financial Performance Summary:\n"
                f"- Total Revenue (TTM): {rev_str}\n"
                f"- Quarterly Revenue Growth (YoY): {growth_str}\n"
                f"- Gross Margin: {gm_str} | Operating Margin: {om_str}\n\n"
                f"Business Description & Market Positioning:\n{summary}\n"
            )

            # Save to articles directory and synchronize index
            filename = self.save_article(clean_ticker, content)
            chunks, _ = self.build_and_persist_index()

            return {
                "ticker": clean_ticker,
                "company_name": name,
                "filename": filename,
                "market_cap": cap_str,
                "revenue": rev_str,
                "indexed_chunks": chunks,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to fetch live financials for {clean_ticker}: {e}")
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Failed to fetch live financial data for '{clean_ticker}': {str(e)}"
                ),
            )

    def build_and_persist_index(
        self, force_rebuild: bool = False
    ) -> tuple[int, list[str]]:
        """Reads corpus files, attaches ticker metadata, strips absolute paths,

        checks file hashes to avoid rebuilding unaffected documents, and persists to storage.
        """
        data_dir = settings.ARTICLES_DIR
        storage_dir = settings.STORAGE_DIR

        files = sorted(
            [f.name for f in data_dir.glob("*.txt")]
            + [f.name for f in data_dir.glob("*.md")]
        )
        if not files:
            logger.info("No documents found in articles directory.")
            return 0, []

        current_hashes = self._compute_hashes()
        stored_hashes = self._load_stored_hashes()
        index_exists = storage_dir.exists() and any(storage_dir.iterdir())

        # If hashes match and storage exists and not forced, avoid redundant re-embedding
        if not force_rebuild and index_exists and current_hashes == stored_hashes:
            logger.info(
                "Article hashes match persisted vector storage. Skipping embedding rebuild."
            )
            return len(files), files

        logger.info(f"Loading documents from {data_dir}...")
        documents = SimpleDirectoryReader(str(data_dir)).load_data()

        # Attach ticker metadata and strip absolute paths
        for doc in documents:
            file_name = doc.metadata.get("file_name") or Path(
                doc.metadata.get("file_path", "")
            ).name
            ticker = Path(file_name).stem.upper()
            doc.metadata["ticker"] = ticker
            doc.metadata["file_name"] = file_name
            # Strip absolute path for hygiene and privacy
            doc.metadata.pop("file_path", None)

        logger.info(
            f"Generating embeddings using local {settings.DEFAULT_EMBED_MODEL}..."
        )
        embed_model = HuggingFaceEmbedding(model_name=settings.DEFAULT_EMBED_MODEL)
        Settings.embed_model = embed_model
        Settings.llm = None  # Indexing does not need active LLM calls

        index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)

        logger.info(f"Persisting vector store to {storage_dir}...")
        index.storage_context.persist(persist_dir=str(storage_dir))
        self._save_stored_hashes(current_hashes)

        # Invalidate any cached query engine
        rag_engine_service.invalidate_cache()
        logger.info(
            f"Indexing complete! {len(documents)} document chunk(s) saved."
        )
        return len(documents), files


article_service = ArticleService()
