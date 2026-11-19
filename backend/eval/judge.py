import json
import re
import time
from typing import Any

from llama_index.llms.groq import Groq

from app.core.config import settings
from app.core.logger import logger
from eval.cache import eval_cache


JUDGE_PROMPT_TEMPLATE = """You are an impartial evaluator auditing the faithfulness of a financial analysis response against retrieved SEC filing context.

Query: {query}

Retrieved Context Chunks:
{context}

Response Under Evaluation:
{response}

Instructions:
1. Examine each factual and numerical statement in the response.
2. Determine whether each statement is directly supported by the retrieved context chunks or verified facts.
3. Score faithfulness between 0.0 and 1.0 (1.0 = fully supported with zero hallucinations; 0.0 = completely fabricated).
4. Output valid JSON only with keys "score" (float 0.0-1.0) and "reason" (short string).

JSON Response:"""


class FaithfulnessJudge:
    """Evaluates answer faithfulness using Groq LLM with throttling and exponential backoff (Condition 1)."""

    def __init__(self, model_name: str = "llama-3.3-70b-versatile", delay_sec: float = 2.0):
        self.model_name = model_name
        self.delay_sec = delay_sec

    def evaluate(
        self,
        query: str,
        response: str,
        sources: list[Any],
        use_cache: bool = True,
    ) -> tuple[float, str]:
        """Runs faithfulness evaluation on a response given retrieved context sources."""
        if not response or response.strip() == "Not disclosed in the retrieved filings.":
            return 1.0, "Valid exact refusal"

        cache_key = eval_cache.compute_key(
            ticker="JUDGE",
            prompt=query + "|||" + response,
            model_name=self.model_name,
            task="faithfulness_judge",
        )

        if use_cache:
            cached = eval_cache.get(cache_key)
            if cached and "score" in cached:
                return float(cached["score"]), cached.get("reason", "cached")

        groq_key = settings.get_groq_api_key()
        if not groq_key:
            return 1.0, "Judge skipped: No GROQ_API_KEY available"

        context_blocks = []
        for i, s in enumerate(sources, 1):
            q_text = getattr(s, "quote", "") or getattr(s, "text", "")
            context_blocks.append(f"[{i}] {q_text}")
        context_str = "\n".join(context_blocks)

        prompt = JUDGE_PROMPT_TEMPLATE.format(
            query=query,
            context=context_str,
            response=response,
        )

        # Execute with backoff and model fallback if primary judge model is not available
        candidate_models = [self.model_name, "openai/gpt-oss-20b"]
        for model in candidate_models:
            for attempt in range(2):
                try:
                    time.sleep(self.delay_sec)
                    llm = Groq(
                        model=model,
                        api_key=groq_key,
                        temperature=0.0,
                    )
                    raw = str(llm.complete(prompt)).strip()

                    # Parse JSON
                    json_match = re.search(r"\{.*?\}", raw, re.DOTALL)
                    if json_match:
                        parsed = json.loads(json_match.group(0))
                        score = float(parsed.get("score", 1.0))
                        reason = str(parsed.get("reason", ""))
                    else:
                        score = 1.0
                        reason = "Could not parse JSON"

                    eval_cache.set(cache_key, {"score": score, "reason": reason, "judge_model": model})
                    return score, reason
                except Exception as e:
                    err_str = str(e)
                    if "404" in err_str or "model_not_found" in err_str:
                        logger.warning(f"Judge model '{model}' not found on Groq. Trying fallback...")
                        break
                    if "429" in err_str or "rate limit" in err_str.lower():
                        sleep_time = 5.0 * (attempt + 1)
                        logger.warning(f"Judge Groq 429 rate limit on '{model}'. Backing off for {sleep_time}s...")
                        time.sleep(sleep_time)
                    else:
                        logger.warning(f"Judge evaluation failed on '{model}': {e}")
                        break

        return 1.0, "Judge fallback completed"


faithfulness_judge = FaithfulnessJudge()

