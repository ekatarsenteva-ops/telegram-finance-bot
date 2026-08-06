import datetime
import logging

from google import genai
from google.genai import errors, types
from pydantic import BaseModel

from config import settings
from models.schemas import ParsedTransaction, SplitParticipant
from prompts.parse_system_prompt import PARSE_SYSTEM_PROMPT
from typing import Literal

logger = logging.getLogger(__name__)

client = genai.Client(api_key=settings.gemini_api_key)

MODEL = "gemini-flash-latest"


class _GeminiParsedTransaction(BaseModel):
    """Same shape as ParsedTransaction, but organization_id is a string —
    Gemini's structured output rejects integer enum values."""

    transaction_type: Literal["income", "expense", "incoming_payment"]
    amount: float
    currency: Literal["RUB", "USD", "EUR"] | None = None
    date: str | None = None
    counterparty: str | None = None
    organization_id: Literal["1", "2"] | None = None
    category: str | None = None
    is_offset: bool = False
    split_participants: list[SplitParticipant] | None = None
    confidence: int
    needs_clarification: list[str] = []

    def to_parsed_transaction(self) -> ParsedTransaction:
        data = self.model_dump()
        data["organization_id"] = int(data["organization_id"]) if data["organization_id"] else None
        return ParsedTransaction(**data)


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
        response = client.models.generate_content(
            model=MODEL,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=PARSE_SYSTEM_PROMPT,
                response_mime_type="application/json",
                response_schema=_GeminiParsedTransaction,
            ),
        )
    except errors.ClientError as exc:
        if exc.code == 429:
            logger.error("Gemini rate limit error: %s", exc)
            return ParseResult(None, "rate_limit", None)
        logger.error("Gemini API client error: %s", exc)
        return ParseResult(None, f"api_error_{exc.code}", None)
    except errors.ServerError as exc:
        logger.error("Gemini API server error: %s", exc)
        return ParseResult(None, f"api_error_{exc.code}", None)
    except errors.APIError as exc:
        logger.error("Gemini API error: %s", exc)
        return ParseResult(None, "connection_error", None)

    if response.parsed is None:
        logger.warning(
            "Gemini failed to parse text: %r (finish_reason=%s)",
            text,
            response.candidates[0].finish_reason if response.candidates else None,
        )
        return ParseResult(None, "refusal", response.text)

    parsed = response.parsed.to_parsed_transaction()
    return ParseResult(parsed, None, response.text)


def match_repayment_name(text: str, candidates: list[str]) -> str | None:
    """Fuzzy-matches a free-text repayment mention to one of the open-debt names,
    handling diminutives/typos (e.g. "Петя" -> "Петр")."""
    if not candidates:
        return None

    options = ", ".join(candidates)
    prompt = (
        f"Список должников: {options}.\n"
        f'Фраза пользователя: "{text}"\n'
        "Если фраза явно указывает на одного из должников из списка (в любой форме имени: "
        "уменьшительной, с опечаткой и т.п.), ответь ТОЛЬКО его именем ТОЧНО как оно "
        "написано в списке. Если не уверен или речь не про этих людей, ответь ТОЛЬКО "
        "словом NONE."
    )

    try:
        response = client.models.generate_content(model=MODEL, contents=prompt)
    except errors.APIError as exc:
        logger.error("Gemini name-match error: %s", exc)
        return None

    answer = (response.text or "").strip()
    return answer if answer in candidates else None
