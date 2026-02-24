"""
AI Service відповідає ТІЛЬКИ за взаємодію з Claude API

Що передається в AI:
  - source: звідки прийшов лід
  - stage: поточний етап
  - messages_count: кількість комунікацій
  - has_business_domain: чи вказаний бізнес-домен

Що AI повертає:
  - score (0.0 - 1.0): вірогідність успішної угоди
  - recommendation: дія для менеджера
  - reason: пояснення

Що AI не вирішує:
  - Чи передавати ліда в продажі
  - Зміну етапів — тільки рекомендує
"""

import json
import re

import anthropic

from app.config import settings
from app.schemas.lead import AIResult

_SYSTEM_PROMPT = """You are a CRM AI assistant that evaluates sales leads.
Analyze the provided lead data and return a JSON object with exactly these fields:
- score: float between 0.0 and 1.0 (probability of successful deal)
- recommendation: one of "transfer_to_sales", "continue_nurturing", "mark_as_lost"
- reason: brief explanation in English (1-2 sentences)

Return ONLY valid JSON, no markdown, no extra text."""

_USER_PROMPT_TEMPLATE = """Evaluate this lead:
- Source: {source}
- Current cold stage: {stage}
- Number of communications: {messages_count}
- Business domain specified: {has_domain}

Return JSON with score, recommendation, reason."""


async def analyze_lead(
    source: str,
    stage: str,
    messages_count: int,
    has_business_domain: bool,
) -> AIResult:
    """
    Викликає Claude API і повертає структурований AIResult
    ValueError якщо API ключ не налаштований
    """
    if not settings.ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY is not configured")

    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    user_message = _USER_PROMPT_TEMPLATE.format(
        source=source,
        stage=stage,
        messages_count=messages_count,
        has_domain="yes" if has_business_domain else "no",
    )

    message = await client.messages.create(
        model="claude-opus-4-6",
        max_tokens=256,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    raw_text = message.content[0].text.strip()

    # Strip markdown code fences if present
    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
    raw_text = re.sub(r"\s*```$", "", raw_text)

    data = json.loads(raw_text)

    return AIResult(
        score=float(data["score"]),
        recommendation=str(data["recommendation"]),
        reason=str(data["reason"]),
    )
