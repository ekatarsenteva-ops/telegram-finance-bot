import datetime
import logging

import anthropic

from config import settings
from models.schemas import ParsedTransaction
from prompts.parse_system_prompt import PARSE_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

MODEL = "claude-sonnet-5"


class ParseResult:
    def __init__(
        self,
        parsed: ParsedTransaction | None,
        error: str | None,
        raw_response_text: str | None,
    ) -> None:
        self.parsed = parsed
        self.error = error
        self.raw_response_text = raw_response_text


def parse_transaction(text: str) -> ParseResult:
    today = datetime.date.today().isoformat()
    user_prompt = f"Сегодняшняя дата: {today}. Распарси операцию: {text}"

    try:
        response = client.messages.parse(
            model=MODEL,
            max_tokens=1024,
            system=PARSE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            output_format=ParsedTransaction,
        )
    except anthropic.RateLimitError as exc:
        logger.error("Claude rate limit error: %s", exc)
        return ParseResult(None, "rate_limit", None)
    except anthropic.APIConnectionError as exc:
        logger.error("Claude connection error: %s", exc)
        return ParseResult(None, "connection_error", None)
    except anthropic.APIStatusError as exc:
        logger.error("Claude API status error: %s", exc)
        return ParseResult(None, f"api_error_{exc.status_code}", None)

    if response.stop_reason == "refusal":
        logger.warning("Claude refused to parse text: %r", text)
        return ParseResult(None, "refusal", None)

    if response.stop_reason == "max_tokens":
        logger.warning("Claude hit max_tokens while parsing text: %r", text)
        return ParseResult(None, "max_tokens", None)

    return ParseResult(response.parsed_output, None, response.model_dump_json())
