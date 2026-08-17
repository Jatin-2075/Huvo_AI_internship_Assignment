import json
import os

from anthropic import Anthropic

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

ANALYTICS_SYSTEM_PROMPT = """You extract structured lead analytics from a real-estate sales chat
transcript between an AI agent (Null, Northstar Homes) and a customer.

Return ONLY a single valid JSON object, no prose, no markdown fences, with
exactly these fields:

- "customer_name": string or null
- "language_used": one of "english", "hindi", "hinglish", "mixed"
- "configuration_interest": one of "2bhk", "3bhk", "undecided", "not discussed"
- "budget_signal": short string describing what the customer indicated about
  budget, or "not discussed"
- "purpose": one of "end-use", "investment", "unknown"
- "interest_level": one of "hot", "warm", "cold"
- "objections_raised": array of short strings (e.g. ["price", "trust"]),
  empty array if none
- "site_visit_status": one of "booked", "booking_failed_no_retry",
  "booking_failed_rescheduled", "not_requested"
- "site_visit_details": short string (date/time/location) or null
- "follow_up_required": boolean
- "follow_up_preference": short string (e.g. "call Saturday evening") or null
- "opted_out": boolean
- "escalated_to_human": boolean
- "summary": one or two sentence plain-language summary of the conversation
"""


def generate_analytics(transcript_text: str) -> dict:
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=ANALYTICS_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": transcript_text}],
    )
    raw = "".join(block.text for block in response.content if block.type == "text").strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"error": "Could not parse analytics JSON", "raw_output": raw}
