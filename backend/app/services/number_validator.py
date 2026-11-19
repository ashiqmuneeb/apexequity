import re
from typing import Any


UNIT_MULTIPLIERS = {
    "trillion": 1e12,
    "t": 1e12,
    "billion": 1e9,
    "b": 1e9,
    "million": 1e6,
    "m": 1e6,
    "thousand": 1e3,
    "k": 1e3,
}

YEAR_PATTERN = re.compile(r"^(19\d\d|20\d\d)$")


class NumberClaim:
    """Represents an extracted numeric claim from LLM text."""

    def __init__(
        self,
        raw_text: str,
        value: float,
        unit: str | None,
        decimals: int,
        start: int,
        end: int,
        has_currency: bool,
        has_percent: bool,
    ):
        self.raw_text = raw_text
        self.value = value
        self.unit = unit
        self.decimals = decimals
        self.start = start
        self.end = end
        self.has_currency = has_currency
        self.has_percent = has_percent

    def __repr__(self) -> str:
        return f"NumberClaim({self.raw_text}, val={self.value}, unit={self.unit}, dec={self.decimals})"


class NumberValidator:
    """Validates financial numerical claims against VERIFIED FACTS and retrieved chunks.

    Only checks currency amounts, percentages, and numbers followed by unit words.
    Ignores years, dates, ordinals, citations, list numbers, and small integers without units.
    Matches by rounding the reference value to the same number of decimals the claim uses.
    """

    # Regex targeting currency ($100, $215.94B), percentages (71.1%, +65.5%),
    # or numbers followed by unit words (215.94 billion, 130,497 million).
    CLAIM_REGEX = re.compile(
        r"(?<!\w)(?P<currency>\\?\$)?(?P<sign>[+-])?(?P<num>\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?)\s*(?P<unit>trillion|billion|million|thousand|[BMTK]|%)?(?!\w)",
        re.IGNORECASE,
    )

    CITATION_REGEX = re.compile(r"\[\d+(?:,\s*\d+)*\]")
    SECTION_REGEX = re.compile(r"\b(?:Item|Form)\s+[0-9A-Z]+", re.IGNORECASE)
    ORDINAL_REGEX = re.compile(r"\b\d+(?:st|nd|rd|th)\b", re.IGNORECASE)

    @classmethod
    def extract_claims(cls, text: str) -> list[NumberClaim]:
        """Extracts eligible financial claims: currency, percentages, or numbers with unit words."""
        claims: list[NumberClaim] = []

        # Mask out citations and section headers to prevent false detection
        masked_text = text
        for match in cls.CITATION_REGEX.finditer(text):
            s, e = match.span()
            masked_text = masked_text[:s] + " " * (e - s) + masked_text[e:]

        for match in cls.SECTION_REGEX.finditer(text):
            s, e = match.span()
            masked_text = masked_text[:s] + " " * (e - s) + masked_text[e:]

        for match in cls.ORDINAL_REGEX.finditer(text):
            s, e = match.span()
            masked_text = masked_text[:s] + " " * (e - s) + masked_text[e:]

        for match in cls.CLAIM_REGEX.finditer(masked_text):
            raw = match.group(0).strip()
            curr = match.group("currency")
            sign = match.group("sign") or ""
            num_str = match.group("num").replace(",", "")
            unit = (match.group("unit") or "").lower()

            has_currency = bool(curr)
            has_percent = unit == "%" or "%" in raw
            has_unit_word = unit in UNIT_MULTIPLIERS

            # Condition 3: ONLY check currency amounts, percentages, and numbers followed by a unit word
            if not (has_currency or has_percent or has_unit_word):
                continue

            # Ignore standalone years (e.g. $2026 is unlikely, but check num without curr/unit)
            if not has_currency and not has_percent and not has_unit_word:
                if YEAR_PATTERN.match(num_str):
                    continue

            # Calculate decimal places
            if "." in num_str:
                decimals = len(num_str.split(".")[1])
            else:
                decimals = 0

            try:
                base_val = float(sign + num_str)
            except ValueError:
                continue

            claims.append(
                NumberClaim(
                    raw_text=raw,
                    value=base_val,
                    unit=unit if unit else ("%" if has_percent else None),
                    decimals=decimals,
                    start=match.start(),
                    end=match.end(),
                    has_currency=has_currency,
                    has_percent=has_percent,
                )
            )

        return claims

    @classmethod
    def _collect_reference_data(
        cls,
        facts_block: str,
        metrics_dict: dict[str, Any] | None,
        source_texts: list[str],
    ) -> tuple[set[str], list[dict[str, Any]]]:
        """Gathers literal tokens and structured reference numbers from facts and sources."""
        literal_strings: set[str] = set()
        numeric_refs: list[dict[str, Any]] = []

        all_text = facts_block + "\n" + "\n".join(source_texts)

        # 1. Literal strings & numbers in text
        for token in re.findall(r"[+-]?\d+(?:,\d{3})*(?:\.\d+)?%?", all_text):
            clean_tok = token.replace(",", "").strip()
            if clean_tok:
                literal_strings.add(clean_tok)
                literal_strings.add(clean_tok.lstrip("+"))
                if clean_tok.endswith("%"):
                    literal_strings.add(clean_tok[:-1])

        # Extract structured numbers from metrics dictionary
        if metrics_dict:
            for key, val in metrics_dict.items():
                if val is None or not isinstance(val, (int, float)):
                    continue
                # Raw currency totals (e.g. 215938000000)
                if "raw" in key or key in ["revenue", "gross_profit", "cost_of_revenue", "prior_revenue", "prior_gross_profit", "prior_cost_of_revenue"]:
                    numeric_refs.append({
                        "kind": "currency",
                        "raw_val": float(val),
                        "key": key,
                    })
                # Percentages (e.g. 71.1, 75.0, 65.5)
                elif "margin" in key or "growth" in key:
                    numeric_refs.append({
                        "kind": "percent",
                        "val": float(val),
                        "key": key,
                    })

        # Also extract structured numbers from facts block text
        for line in facts_block.splitlines():
            # e.g. - Revenue: $215.94B (215,938,000,000 USD)
            raw_match = re.search(r"\((\d[\d,]+)\s*USD\)", line)
            if raw_match:
                val = float(raw_match.group(1).replace(",", ""))
                numeric_refs.append({"kind": "currency", "raw_val": val, "key": "facts_block"})
            # e.g. - Gross Margin: 71.1%
            pct_matches = re.findall(r"([+-]?\d+(?:\.\d+)?)\s*%", line)
            for pm in pct_matches:
                numeric_refs.append({"kind": "percent", "val": float(pm), "key": "facts_block"})

        # Also parse claims in sources
        source_claims = cls.extract_claims(all_text)
        for sc in source_claims:
            if sc.has_percent:
                numeric_refs.append({"kind": "percent", "val": sc.value, "key": "source_text"})
            elif sc.has_currency or sc.unit in UNIT_MULTIPLIERS:
                multiplier = UNIT_MULTIPLIERS.get(sc.unit or "", 1.0)
                numeric_refs.append({"kind": "currency", "raw_val": sc.value * multiplier, "key": "source_text"})

        return literal_strings, numeric_refs

    @classmethod
    def validate(
        cls,
        text: str,
        facts_block: str,
        metrics_dict: dict[str, Any] | None,
        source_texts: list[str],
    ) -> tuple[str, list[str]]:
        """Validates all claims in text against facts and sources.

        Marks unsupported numbers with [unverified] inline and appends a warning line.
        """
        claims = cls.extract_claims(text)
        if not claims:
            return text, []

        literal_strings, numeric_refs = cls._collect_reference_data(
            facts_block, metrics_dict, source_texts
        )

        unsupported_claims: list[NumberClaim] = []

        for claim in claims:
            is_supported = False
            clean_num_str = str(claim.value)

            # Check literal match first
            if clean_num_str in literal_strings or claim.raw_text.lstrip("$+").rstrip("%") in literal_strings:
                is_supported = True

            # Check numerical rounding match
            if not is_supported:
                d = claim.decimals

                if claim.has_percent or claim.unit == "%":
                    # Check percent references
                    for ref in numeric_refs:
                        if ref["kind"] == "percent":
                            ref_val = ref["val"]
                            # Round reference value to same decimals as claim
                            if round(ref_val, d) == round(claim.value, d):
                                is_supported = True
                                break
                            # Also check absolute difference for floating point accuracy (< 1e-4)
                            if abs(ref_val - claim.value) < 1e-4:
                                is_supported = True
                                break

                elif claim.has_currency or (claim.unit in UNIT_MULTIPLIERS):
                    multiplier = UNIT_MULTIPLIERS.get(claim.unit or "", 1.0)
                    claim_abs = claim.value * multiplier

                    for ref in numeric_refs:
                        if ref["kind"] == "currency":
                            ref_abs = ref["raw_val"]
                            # Round reference in the claimed unit
                            ref_in_unit = ref_abs / multiplier if multiplier != 0 else ref_abs
                            if round(ref_in_unit, d) == round(claim.value, d):
                                is_supported = True
                                break
                            if abs(ref_abs - claim_abs) < 1.0:
                                is_supported = True
                                break

            if not is_supported:
                unsupported_claims.append(claim)

        if not unsupported_claims:
            return text, []

        # Tag unsupported claims in text in reverse order so offsets remain valid
        modified_text = text
        unsupported_strings: list[str] = []

        for claim in reversed(unsupported_claims):
            unsupported_strings.append(claim.raw_text)
            end = claim.end
            # Insert [unverified] right after the claim
            modified_text = (
                modified_text[:end] + " [unverified]" + modified_text[end:]
            )

        unsupported_strings.reverse()
        warning_line = (
            f"\n\n⚠️ Warning: Contains unverified numerical claims not supported by SEC filings: "
            f"{', '.join(unsupported_strings)}."
        )
        final_text = modified_text + warning_line

        return final_text, unsupported_strings


number_validator = NumberValidator()
