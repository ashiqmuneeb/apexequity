from pathlib import Path
from typing import List, Tuple
from fastapi import HTTPException
from llama_index.core import SimpleDirectoryReader, StorageContext, VectorStoreIndex, Settings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from app.core.config import settings
from app.core.logger import logger
from app.schemas.article import ArticleItem
from app.services.rag_engine import rag_engine_service


class ArticleService:
    """Handles financial document corpus operations and vector indexing."""

    def __init__(self):
        settings.ARTICLES_DIR.mkdir(parents=True, exist_ok=True)
        settings.STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    def list_articles(self) -> List[ArticleItem]:
        """Lists all corporate reports and articles in the corpus."""
        items: List[ArticleItem] = []
        files = sorted(settings.ARTICLES_DIR.glob("*.txt")) + sorted(settings.ARTICLES_DIR.glob("*.md"))
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
        """Saves or updates a stock article file."""
        clean_ticker = ticker.strip().upper().replace(" ", "_")
        if not clean_ticker:
            raise HTTPException(status_code=400, detail="Stock ticker symbol is required.")

        file_path = settings.ARTICLES_DIR / f"{clean_ticker}.txt"
        file_path.write_text(content.strip(), encoding="utf-8")
        logger.info(f"Article saved for ticker: {clean_ticker}")
        return f"{clean_ticker}.txt"

    def delete_article(self, ticker: str) -> None:
        """Deletes an article file for a given ticker."""
        clean_ticker = ticker.strip().upper()
        file_path = settings.ARTICLES_DIR / f"{clean_ticker}.txt"
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"Article for {clean_ticker} not found.")

        file_path.unlink()
        logger.info(f"Article deleted for ticker: {clean_ticker}")

    def fetch_live_stock_data(self, ticker: str) -> dict:
        """Fetches real-time financial statements and company profile from Yahoo Finance,
        saves to ./articles, and rebuilds the vector index."""
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
                    detail=f"Could not find financial market data for ticker symbol '{clean_ticker}'.",
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

            # Compile into an authoritative financial report document
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

            # Save to articles directory
            filename = self.save_article(clean_ticker, content)

            # Rebuild vector index so LlamaIndex can immediately retrieve and analyze it
            chunks, files = self.build_and_persist_index()

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
                detail=f"Failed to fetch live financial data for '{clean_ticker}': {str(e)}",
            )

    def build_and_persist_index(self) -> Tuple[int, List[str]]:
        """Reads corpus files, generates local BGE embeddings, and persists to storage."""
        data_dir = settings.ARTICLES_DIR
        storage_dir = settings.STORAGE_DIR

        files = [f.name for f in data_dir.glob("*.txt")] + [f.name for f in data_dir.glob("*.md")]
        if not files:
            # Seed default sample files if empty
            (data_dir / "NVDA.txt").write_text(
                "NVIDIA Corporation (NVDA) reported record Q4 revenue of $22.1 billion, up 265% from a year ago. "
                "Growth was driven by massive enterprise demand for H100 Tensor Core GPUs and Hopper architecture. "
                "Data Center revenue grew 409% year-over-year to $18.4 billion. Key risks include export control restrictions and supply chain limits.",
                encoding="utf-8",
            )
            (data_dir / "GOOGL.txt").write_text(
                "Alphabet Inc. (GOOGL) reported Q4 revenue of $86.3 billion, up 13% YoY, propelled by Search and Google Cloud momentum. "
                "Google Cloud reached $9.19 billion in revenue with expanding operating margins. "
                "Alphabet continues heavy capital expenditure into Gemini AI infrastructure. Key risks include digital ad market shifts and antitrust litigation.",
                encoding="utf-8",
            )
            files = ["NVDA.txt", "GOOGL.txt"]

        logger.info(f"Loading documents from {data_dir}...")
        documents = SimpleDirectoryReader(str(data_dir)).load_data()

        logger.info(f"Generating embeddings using local {settings.DEFAULT_EMBED_MODEL}...")
        embed_model = HuggingFaceEmbedding(model_name=settings.DEFAULT_EMBED_MODEL)
        Settings.embed_model = embed_model
        Settings.llm = None  # Indexing does not need active LLM calls

        index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)

        logger.info(f"Persisting vector store to {storage_dir}...")
        index.storage_context.persist(persist_dir=str(storage_dir))

        # Invalidate any cached query engine
        rag_engine_service.invalidate_cache()
        logger.info(f"Indexing complete! {len(documents)} document chunk(s) saved.")
        return len(documents), files


article_service = ArticleService()

