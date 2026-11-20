import re
from pathlib import Path

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

from app.core.config import settings
from app.core.logger import logger


def is_valid_body_chunk(text: str, min_words: int = 40, exempt_tables: bool | None = None) -> bool:
    """Checks whether a chunk contains genuine body text and is not merely a heading or TOC snippet.

    Skips chunks that contain only a heading and drops chunks with fewer than 40 words of body text,
    unless table exemption is enabled and the chunk represents a concise numerical/financial table (Condition 5).
    """
    clean_text = text.strip()
    if not clean_text:
        return False

    lines = clean_text.splitlines()
    body_lines: list[str] = []
    for line in lines:
        l_str = line.strip()
        if not l_str:
            continue
        # Exclude headers, item markers, TOC dividers, and markdown horizontal rules
        if re.match(r"^(=+|-+|\*+|#+)\s*", l_str):
            continue
        if re.match(r"^(ITEM|PART)\s+[0-9A-Za-z]+", l_str, re.IGNORECASE):
            continue
        if re.match(r"^Table of Contents", l_str, re.IGNORECASE):
            continue
        body_lines.append(l_str)

    body_text = " ".join(body_lines)
    words = re.findall(r"\b[A-Za-z0-9'-]+\b", body_text)

    # Condition 5: Table-chunk exemption (many numbers, few words or table delimiters)
    should_exempt = exempt_tables if exempt_tables is not None else getattr(settings, "TABLE_EXEMPTION_ENABLED", True)
    if should_exempt:
        numbers = re.findall(r"[\$]?\d[\d,]*\.?\d*%?", body_text)
        # If chunk contains >= 3 numeric figures or table formatting, exempt from word threshold
        if len(numbers) >= 3 or ("|" in body_text and len(numbers) >= 2):
            return len(words) >= 5

    return len(words) >= min_words


class SectionAwareChunker:
    """Splits Form 10-K filings into Items (1, 1A, 7, 8) and chunks them with rich metadata."""

    def __init__(self, chunk_size: int | None = None, chunk_overlap: int | None = None):
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.splitter = SentenceSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
        )

    @staticmethod
    def parse_metadata_header(text: str, file_path: Path) -> dict[str, str | int]:
        """Extracts filing metadata from [DOCUMENT_METADATA] header if present."""
        clean_name = file_path.name
        ticker = file_path.stem.split("_")[0].upper()
        form = "10-K" if "_10K" in clean_name.upper() else "Document"
        fy: int | str = "N/A"
        period_end = "N/A"
        accn = "N/A"

        meta_match = re.search(
            r"\[DOCUMENT_METADATA\](.*?)\[/DOCUMENT_METADATA\]", text, re.DOTALL
        )
        if meta_match:
            header_content = meta_match.group(1)
            t_match = re.search(r"Ticker:\s*([A-Za-z0-9_-]+)", header_content)
            if t_match:
                ticker = t_match.group(1).strip().upper()

            f_match = re.search(r"Form:\s*([A-Za-z0-9_-]+)", header_content)
            if f_match:
                form = f_match.group(1).strip()

            fy_match = re.search(r"Fiscal Year:\s*(\d{4})", header_content)
            if fy_match:
                fy = int(fy_match.group(1).strip())

            pe_match = re.search(r"Period End Date:\s*([0-9-]+)", header_content)
            if pe_match:
                period_end = pe_match.group(1).strip()

            ac_match = re.search(r"Accession Number:\s*([0-9-]+)", header_content)
            if ac_match:
                accn = ac_match.group(1).strip()

        return {
            "ticker": ticker,
            "form": form,
            "fiscal_year": fy,
            "period_end": period_end,
            "accession_number": accn,
            "file_name": clean_name,  # Relative path only
            "source": clean_name,
        }

    def split_into_sections(self, text: str) -> list[tuple[str, str]]:
        """Extracts Item 1, Item 1A, Item 7, Item 8 blocks from the filing text."""
        # Remove document metadata header from chunkable content
        body = re.sub(
            r"\[DOCUMENT_METADATA\].*?\[/DOCUMENT_METADATA\]", "", text, flags=re.DOTALL
        ).strip()

        pattern = re.compile(r"===\s*(ITEM\s+[0-9A-Za-z]+)\s*===", re.IGNORECASE)
        splits = list(pattern.finditer(body))
        if not splits:
            return [("General", body)]

        sections: list[tuple[str, str]] = []
        for i, match in enumerate(splits):
            item_raw = match.group(1).strip()
            # Normalize title, e.g. "ITEM 1A" -> "Item 1A"
            item_name = " ".join(
                word.capitalize() if idx == 0 else word.upper()
                for idx, word in enumerate(item_raw.split())
            )
            start_pos = match.end()
            end_pos = splits[i + 1].start() if i + 1 < len(splits) else len(body)
            section_content = body[start_pos:end_pos].strip()

            # Skip empty or placeholder sections
            if not section_content or "not found as separate text section" in section_content:
                continue

            sections.append((item_name, section_content))

        return sections if sections else [("General", body)]

    def chunk_file(self, file_path: Path, text: str) -> list[TextNode]:
        """Parses a 10-K file into section-aware chunks with attached metadata."""
        meta = self.parse_metadata_header(text, file_path)
        sections = self.split_into_sections(text)

        all_nodes: list[TextNode] = []
        for section_name, section_text in sections:
            # Chunk section content
            chunks = self.splitter.split_text(section_text)
            valid_idx = 0
            for raw_chunk in chunks:
                chunk = raw_chunk.strip()
                # Condition: Skip chunks that contain only a heading; drop if < 40 words of body text
                if not is_valid_body_chunk(chunk, min_words=40):
                    continue

                chunk_meta = dict(meta)
                chunk_meta["section"] = section_name
                chunk_meta["chunk_index"] = valid_idx

                # Build clean unique node id
                node_id = f"{meta['ticker']}_{meta['fiscal_year']}_{section_name.replace(' ', '_')}_{valid_idx}"
                valid_idx += 1

                node = TextNode(
                    id_=node_id,
                    text=chunk,
                    metadata=chunk_meta,
                    excluded_embed_metadata_keys=[
                        "file_name",
                        "source",
                        "accession_number",
                        "chunk_index",
                    ],
                    excluded_llm_metadata_keys=[
                        "file_name",
                        "source",
                        "chunk_index",
                    ],
                )
                all_nodes.append(node)

        logger.debug(
            f"Chunked {file_path.name} into {len(all_nodes)} nodes across {len(sections)} sections."
        )
        return all_nodes


section_chunker = SectionAwareChunker()

