import hashlib
import json
from pathlib import Path

from fastapi import HTTPException

from app.core.config import settings
from app.core.logger import logger
from app.schemas.article import ArticleItem
from app.services.chunking_service import section_chunker
from app.services.rag_engine import rag_engine_service
from app.services.retrieval_service import retrieval_service


class ArticleService:
    """Handles financial document corpus operations and vector indexing.

    Attaches ticker metadata, strips absolute paths, updates index on delete,
    and caches file hashes to avoid rebuilding unaffected documents.
    """

    def __init__(self):
        settings.ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
        settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def _get_indexable_files(self) -> list[Path]:
        """Returns files to index.

        Excludes AMD.txt (undated snapshot) from vector index if AMD_10K.txt exists (Requirement 4).
        """
        all_files = sorted(settings.ARTICLES_DIR.glob("*.txt")) + sorted(
            settings.ARTICLES_DIR.glob("*.md")
        )
        has_amd_10k = any(f.name.upper().startswith("AMD_10K") for f in all_files)
        indexable: list[Path] = []
        for f in all_files:
            if has_amd_10k and f.name.upper() == "AMD.TXT":
                logger.info(
                    "Excluding AMD.txt (undated Yahoo snapshot) from vector index because AMD_10K.txt exists."
                )
                continue
            indexable.append(f)
        return indexable

    CHUNKER_VERSION = "v3_tables_item15"

    def _compute_hashes(self) -> dict[str, str]:
        """Computes SHA256 hashes of indexable text files, salted with chunker version and settings

        so vector storage automatically rebuilds whenever chunk filtering or chunk sizing changes (Condition 7).
        """
        hashes = {}
        files = self._get_indexable_files()
        chunk_signature = f"{self.CHUNKER_VERSION}_{settings.CHUNK_SIZE}_{settings.CHUNK_OVERLAP}"
        for f in files:
            try:
                content = f.read_bytes()
                combined = content + f"__CHUNK_SIG_{chunk_signature}__".encode()
                hashes[f.name] = hashlib.sha256(combined).hexdigest()
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
                ticker = file.stem.split("_")[0].upper()
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
        """Deletes an article file for a given ticker and removes it from Chroma vector store."""
        clean_ticker = ticker.strip().upper()
        file_path = settings.ARTICLES_DIR / f"{clean_ticker}.txt"
        if not file_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Article for {clean_ticker} not found."
            )

        file_path.unlink()
        logger.info(f"Article file deleted for ticker: {clean_ticker}")

        # Purge chunks from Chroma
        try:
            col = retrieval_service.get_collection()
            col.delete(where={"ticker": clean_ticker})
        except Exception as e:
            logger.warning(f"Error purging {clean_ticker} from Chroma: {e}")

        # Remove from stored hashes
        stored_hashes = self._load_stored_hashes()
        stored_hashes.pop(f"{clean_ticker}.txt", None)
        self._save_stored_hashes(stored_hashes)

        # Invalidate retrieval caches
        retrieval_service.invalidate_cache()
        rag_engine_service.invalidate_cache()
        logger.info(f"Vector storage updated after deleting {clean_ticker}")

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

            summary = info.get("longBusinessSummary", "No corporate summary available.")

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
        """Parses corpus files using section-aware chunker, indexes into persistent Chroma,

        re-embeds only files whose hash changed, and logs step-by-step progress.
        """
        indexable_files = self._get_indexable_files()
        file_names = [f.name for f in indexable_files]
        if not indexable_files:
            logger.info("No documents found in articles directory.")
            return 0, []

        current_hashes = self._compute_hashes()
        stored_hashes = self._load_stored_hashes()
        col = retrieval_service.get_collection()

        # Determine which files need indexing
        collection_empty = col.count() == 0
        files_to_index: list[Path] = []
        for f in indexable_files:
            if force_rebuild or collection_empty or stored_hashes.get(f.name) != current_hashes.get(f.name):
                files_to_index.append(f)

        # Handle deleted files
        deleted_file_names = set(stored_hashes.keys()) - set(current_hashes.keys())
        for dfn in deleted_file_names:
            logger.info(f"Removing deleted file '{dfn}' from vector store...")
            try:
                col.delete(where={"file_name": dfn})
            except Exception as e:
                logger.warning(f"Error deleting chunks for {dfn}: {e}")
            stored_hashes.pop(dfn, None)

        if not files_to_index and not deleted_file_names and not force_rebuild and col.count() > 0:
            logger.info(
                "Article hashes match persisted Chroma vector storage. Skipping embedding rebuild."
            )
            count = col.count()
            return count, file_names

        logger.info(
            f"Indexing {len(files_to_index)} changed/new document(s) of {len(indexable_files)} total..."
        )

        embed_model = retrieval_service._get_embed_model()
        total_indexed_chunks = 0

        for idx, f in enumerate(files_to_index):
            logger.info(f"[{idx + 1}/{len(files_to_index)}] Processing {f.name}...")
            content = f.read_text(encoding="utf-8")

            # Remove prior chunks for this file if present
            try:
                col.delete(where={"file_name": f.name})
            except Exception:
                pass

            nodes = section_chunker.chunk_file(f, content)
            if not nodes:
                logger.warning(f"No chunks extracted from {f.name}")
                stored_hashes[f.name] = current_hashes[f.name]
                continue

            logger.info(
                f"[{idx + 1}/{len(files_to_index)}] Embedding {len(nodes)} chunks for {f.name} "
                f"with local {settings.DEFAULT_EMBED_MODEL} on CPU..."
            )

            # Batch embeddings to avoid memory spikes
            batch_size = 32
            for b_idx in range(0, len(nodes), batch_size):
                batch_nodes = nodes[b_idx : b_idx + batch_size]
                texts = [n.get_content() for n in batch_nodes]
                embeddings = embed_model.get_text_embedding_batch(texts)

                ids = [n.node_id for n in batch_nodes]
                metas = [n.metadata for n in batch_nodes]

                col.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metas,
                )

            total_indexed_chunks += len(nodes)
            stored_hashes[f.name] = current_hashes[f.name]
            logger.info(
                f"[{idx + 1}/{len(files_to_index)}] Finished {f.name}: {len(nodes)} chunks stored."
            )

        self._save_stored_hashes(stored_hashes)

        # Invalidate in-memory BM25 index and query caches
        retrieval_service.invalidate_cache()
        rag_engine_service.invalidate_cache()

        total_chunks = col.count()
        logger.info(f"Indexing complete! Collection contains {total_chunks} chunk(s).")
        return total_chunks, file_names


article_service = ArticleService()
