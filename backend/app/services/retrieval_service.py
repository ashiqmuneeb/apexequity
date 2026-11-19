import re
import time
from typing import Any

import chromadb
from llama_index.core.embeddings import BaseEmbedding
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from app.core.config import settings
from app.core.logger import logger
from app.schemas.analysis import SourceEvidenceNode


class RetrievalService:
    """Orchestrates hybrid retrieval (dense Chroma + BM25 with reciprocal rank fusion)

    and optional CPU CrossEncoder reranking. Caches BM25 indexes in memory per ticker.
    """

    def __init__(self):
        settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self._chroma_client: chromadb.ClientAPI | None = None
        self._embed_model: BaseEmbedding | None = None
        self._reranker: CrossEncoder | None = None
        self._reranker_model_name: str | None = None
        # In-memory BM25 index cache: {ticker: (BM25Okapi, list[dict_of_doc_data])}
        self._bm25_cache: dict[str, tuple[BM25Okapi, list[dict[str, Any]]]] = {}
        # Stores last measured reranker latency in seconds
        self.last_rerank_latency: float = 0.0

    def invalidate_cache(self) -> None:
        """Clears in-memory BM25 index and cached client when vector index is modified."""
        logger.info("Invalidating in-memory BM25 index and retrieval cache.")
        self._bm25_cache.clear()
        self._chroma_client = None

    def _get_chroma_client(self) -> chromadb.ClientAPI:
        if self._chroma_client is None:
            self._chroma_client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        return self._chroma_client

    def get_collection(self) -> chromadb.Collection:
        client = self._get_chroma_client()
        return client.get_or_create_collection(
            name="stock_filings",
            metadata={"hnsw:space": "cosine"},
        )

    def _get_embed_model(self) -> BaseEmbedding:
        if self._embed_model is None:
            self._embed_model = HuggingFaceEmbedding(
                model_name=settings.DEFAULT_EMBED_MODEL
            )
        return self._embed_model

    def _get_reranker(self) -> CrossEncoder | None:
        if not settings.RERANKER_ENABLED:
            return None
        target_model = settings.RERANKER_MODEL
        if self._reranker is None or self._reranker_model_name != target_model:
            logger.info(f"Loading CPU CrossEncoder reranker: '{target_model}'...")
            try:
                self._reranker = CrossEncoder(target_model, max_length=512)
                self._reranker_model_name = target_model
            except Exception as e:
                logger.warning(
                    f"Failed to load configured reranker '{target_model}': {e}. "
                    "Falling back to 'cross-encoder/ms-marco-MiniLM-L-6-v2'..."
                )
                self._reranker = CrossEncoder(
                    "cross-encoder/ms-marco-MiniLM-L-6-v2", max_length=512
                )
                self._reranker_model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
        return self._reranker

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\w+", text.lower())

    def _get_or_build_bm25(self, ticker: str | None = None) -> tuple[BM25Okapi, list[dict[str, Any]]]:
        """Retrieves or builds in-memory BM25 index for a ticker (Condition 4)."""
        cache_key = ticker.upper() if ticker else "ALL"
        if cache_key in self._bm25_cache:
            return self._bm25_cache[cache_key]

        col = self.get_collection()
        where_filter = {"ticker": cache_key} if cache_key != "ALL" else None

        # Fetch all matching documents and metadata
        raw_res = col.get(
            where=where_filter,
            include=["documents", "metadatas"],
        )

        docs = raw_res.get("documents") or []
        metadatas = raw_res.get("metadatas") or []
        ids = raw_res.get("ids") or []

        chunk_records: list[dict[str, Any]] = []
        tokenized_corpus: list[list[str]] = []

        for i, text in enumerate(docs):
            if not text:
                continue
            meta = metadatas[i] if i < len(metadatas) else {}
            cid = ids[i] if i < len(ids) else f"chunk_{i}"
            record = {"id": cid, "text": text, "metadata": meta}
            chunk_records.append(record)
            tokenized_corpus.append(self._tokenize(text))

        if not tokenized_corpus:
            # Empty index fallback
            bm25 = BM25Okapi([["empty"]])
        else:
            bm25 = BM25Okapi(tokenized_corpus)

        self._bm25_cache[cache_key] = (bm25, chunk_records)
        logger.info(
            f"Built in-memory BM25 index for ticker '{cache_key}' ({len(chunk_records)} chunks)."
        )
        return bm25, chunk_records

    @staticmethod
    def extract_target_year(query: str) -> int | None:
        """Extracts 4-digit fiscal year if explicitly referenced in query."""
        year_matches = re.findall(r"\b(20[12]\d)\b", query)
        if year_matches:
            return int(year_matches[0])
        return None

    def retrieve_candidates_for_ticker(
        self,
        ticker: str,
        query: str,
        dense_top_k: int | None = None,
        bm25_top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """Executes dense + BM25 hybrid search fused via Reciprocal Rank Fusion."""
        clean_ticker = ticker.strip().upper()
        col = self.get_collection()
        k_dense = dense_top_k or settings.DENSE_TOP_K
        k_bm25 = bm25_top_k or settings.BM25_TOP_K

        # Check for explicit year in query
        target_year = self.extract_target_year(query)

        # 1. Dense retrieval
        where_dense: dict[str, Any] = {"ticker": clean_ticker}
        if target_year:
            where_dense = {
                "$and": [
                    {"ticker": clean_ticker},
                    {"fiscal_year": target_year},
                ]
            }

        embed_model = self._get_embed_model()
        query_embedding = embed_model.get_query_embedding(query)

        try:
            dense_res = col.query(
                query_embeddings=[query_embedding],
                n_results=k_dense,
                where=where_dense,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            # If compound filter fails (e.g. no documents with that year), fallback to ticker filter
            logger.debug(f"Year filter query fallback: {e}")
            dense_res = col.query(
                query_embeddings=[query_embedding],
                n_results=k_dense,
                where={"ticker": clean_ticker},
                include=["documents", "metadatas", "distances"],
            )

        dense_ranked: list[dict[str, Any]] = []
        if dense_res and dense_res["ids"] and dense_res["ids"][0]:
            ids = dense_res["ids"][0]
            docs = dense_res["documents"][0] if dense_res["documents"] else []
            metas = dense_res["metadatas"][0] if dense_res["metadatas"] else []
            dists = dense_res["distances"][0] if dense_res["distances"] else []

            for rank, cid in enumerate(ids):
                # Cosine distance to similarity: 1 - dist
                score = round(1.0 - dists[rank], 4) if rank < len(dists) else 0.5
                dense_ranked.append({
                    "id": cid,
                    "text": docs[rank] if rank < len(docs) else "",
                    "metadata": metas[rank] if rank < len(metas) else {},
                    "dense_score": score,
                    "dense_rank": rank + 1,
                })

        # 2. BM25 retrieval
        bm25, chunk_records = self._get_or_build_bm25(clean_ticker)
        tokenized_q = self._tokenize(query)

        bm25_scores = bm25.get_scores(tokenized_q)
        top_indices = sorted(
            range(len(bm25_scores)), key=lambda i: bm25_scores[i], reverse=True
        )[:k_bm25]

        bm25_ranked: list[dict[str, Any]] = []
        for rank, idx in enumerate(top_indices):
            if idx < len(chunk_records) and bm25_scores[idx] > 0.0:
                rec = chunk_records[idx]
                bm25_ranked.append({
                    "id": rec["id"],
                    "text": rec["text"],
                    "metadata": rec["metadata"],
                    "bm25_score": round(float(bm25_scores[idx]), 4),
                    "bm25_rank": rank + 1,
                })

        # 3. Reciprocal Rank Fusion (RRF)
        rrf_k = settings.RRF_K
        fused: dict[str, dict[str, Any]] = {}

        for item in dense_ranked:
            cid = item["id"]
            rrf_score = 1.0 / (rrf_k + item["dense_rank"])
            fused[cid] = {
                "id": cid,
                "text": item["text"],
                "metadata": item["metadata"],
                "retrieval_score": rrf_score,
                "dense_score": item.get("dense_score"),
            }

        for item in bm25_ranked:
            cid = item["id"]
            rrf_score = 1.0 / (rrf_k + item["bm25_rank"])
            if cid in fused:
                fused[cid]["retrieval_score"] += rrf_score
            else:
                fused[cid] = {
                    "id": cid,
                    "text": item["text"],
                    "metadata": item["metadata"],
                    "retrieval_score": rrf_score,
                    "dense_score": None,
                }

        sorted_candidates = sorted(
            fused.values(), key=lambda x: x["retrieval_score"], reverse=True
        )
        return sorted_candidates

    def rerank_and_select(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_n: int | None = None,
    ) -> list[SourceEvidenceNode]:
        """Optionally applies CrossEncoder CPU reranker and builds final SourceEvidenceNode objects."""
        n_final = top_n or settings.TOP_N_RERANK
        if not candidates:
            return []

        reranker = self._get_reranker()
        self.last_rerank_latency = 0.0

        if reranker is not None and candidates:
            pairs = [(query, c["text"]) for c in candidates]
            t0 = time.perf_counter()
            try:
                scores = reranker.predict(pairs)
                self.last_rerank_latency = round(time.perf_counter() - t0, 3)
                logger.info(
                    f"CrossEncoder reranked {len(candidates)} candidates in {self.last_rerank_latency}s."
                )
                for i, c in enumerate(candidates):
                    c["rerank_score"] = round(float(scores[i]), 4)

                candidates.sort(key=lambda x: x["rerank_score"], reverse=True)
            except Exception as e:
                logger.warning(f"Reranker scoring failed: {e}. Falling back to RRF order.")
                for c in candidates:
                    c["rerank_score"] = None
        else:
            for c in candidates:
                c["rerank_score"] = None

        final_candidates = candidates[:n_final]

        # Convert to SourceEvidenceNode schema
        sources: list[SourceEvidenceNode] = []
        for c in final_candidates:
            meta = c.get("metadata", {})
            full_text = c.get("text", "")
            # Quote capped at 300 characters
            quote = full_text[:300].strip()
            if len(full_text) > 300:
                quote += "..."

            r_score = round(float(c.get("retrieval_score") or 0.0), 4)
            rr_score = round(float(c.get("rerank_score")), 4) if c.get("rerank_score") is not None else None

            sources.append(
                SourceEvidenceNode(
                    ticker=meta.get("ticker"),
                    form=meta.get("form", "10-K"),
                    fiscal_year=meta.get("fiscal_year"),
                    period_end=meta.get("period_end"),
                    section=meta.get("section", "Item 1"),
                    accession_number=meta.get("accession_number"),
                    quote=quote,
                    retrieval_score=r_score,
                    rerank_score=rr_score,
                    score=rr_score if rr_score is not None else r_score,
                    text=quote,
                    metadata=meta,
                )
            )

        return sources

    def retrieve_single(
        self,
        ticker: str,
        query: str,
        top_n: int | None = None,
    ) -> list[SourceEvidenceNode]:
        """Hybrid retrieval + reranking strictly isolated for a single ticker."""
        candidates = self.retrieve_candidates_for_ticker(ticker, query)
        return self.rerank_and_select(query, candidates, top_n=top_n)

    def retrieve_compare(
        self,
        stock_a: str,
        stock_b: str,
        query: str,
        top_n: int | None = None,
    ) -> tuple[list[SourceEvidenceNode], list[SourceEvidenceNode]]:
        """Retrieves chunks separately per ticker to guarantee zero cross-contamination."""
        sources_a = self.retrieve_single(stock_a, query, top_n=top_n)
        sources_b = self.retrieve_single(stock_b, query, top_n=top_n)
        return sources_a, sources_b


retrieval_service = RetrievalService()

