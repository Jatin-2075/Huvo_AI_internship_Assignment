"""
Thin wrapper around the Google Gen AI SDK (the current unified SDK,
successor to the deprecated google-generativeai package).

Handles:
- calling the model with the Northstar system prompt + conversation history
- exposing two tools the agent can call: book_site_visit, escalate_to_human
- executing those tools locally (simulated backend actions) and feeding the
  result back to the model so it can respond naturally

Requires: pip install google-genai
Env vars: GEMINI_API_KEY (required), GEMINI_MODEL (optional, defaults below)
"""
import os
import random
from datetime import datetime

from google import genai
from google.genai import types

from app.prompt import SYSTEM_PROMPT

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

TOOLS = [
    types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="book_site_visit",
                description=(
                    "Attempt to book a site visit to Northstar One, Sector 79, "
                    "Gurugram for the customer. Call this once you have a preferred "
                    "date and time from the customer."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "preferred_date": {
                            "type": "string",
                            "description": "Customer's preferred visit date, in whatever form they gave it (e.g. 'this Saturday', '20 Aug').",
                        },
                        "preferred_time": {
                            "type": "string",
                            "description": "Customer's preferred visit time (e.g. '11 AM', 'evening').",
                        },
                        "customer_name": {
                            "type": "string",
                            "description": "Customer's name if known, otherwise 'Unknown'.",
                        },
                    },
                    "required": ["preferred_date", "preferred_time"],
                },
            ),
            types.FunctionDeclaration(
                name="escalate_to_human",
                description=(
                    "Hand off the conversation to a human Northstar Homes advisor. "
                    "Call this for pricing negotiation, complaints, legal/loan "
                    "questions, explicit requests for a human, or repeated booking "
                    "failures."
                ),
                parameters={
                    "type": "object",
                    "properties": {
                        "reason": {
                            "type": "string",
                            "description": "Short reason for escalating.",
                        }
                    },
                    "required": ["reason"],
                },
            ),
        ]
    )
]

GENERATE_CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=TOOLS,
)


def _simulate_booking(preferred_date: str, preferred_time: str, customer_name: str = "Unknown") -> dict:
    """
    Simulated backend booking call. ~70% of slots succeed; the rest fail
    with a reason and (sometimes) alternate suggestions, so the agent has
    to demonstrate real failure-handling behaviour.
    """
    success = random.random() < 0.7
    if success:
        return {
            "status": "confirmed",
            "date": preferred_date,
            "time": preferred_time,
            "location": "Northstar One, Sector 79, Gurugram",
            "booking_ref": f"NS-{random.randint(10000, 99999)}",
        }
    return {
        "status": "failed",
        "reason": "Requested slot is unavailable (site team fully booked at that time).",
        "alternate_slots": ["next day, 11:00 AM", "same day, 4:00 PM"],
    }


def _simulate_escalation(reason: str) -> dict:
    return {
        "status": "escalated",
        "reason": reason,
        "escalated_at": datetime.utcnow().isoformat() + "Z",
        "note": "A human Northstar Homes advisor has been notified and will follow up.",
    }


def _execute_tool(name: str, tool_input: dict) -> dict:
    if name == "book_site_visit":
        return _simulate_booking(
            tool_input.get("preferred_date", ""),
            tool_input.get("preferred_time", ""),
            tool_input.get("customer_name", "Unknown"),
        )
    if name == "escalate_to_human":
        return _simulate_escalation(tool_input.get("reason", "Not specified"))
    return {"status": "error", "reason": f"Unknown tool: {name}"}


def get_agent_reply(history: list[dict]) -> tuple[str, list[dict]]:
    """
    history: list of {"role": "user"|"model", "parts": [...]}
    (No separate "system" role here; the system prompt is passed via
    GENERATE_CONFIG.system_instruction on every call instead.)

    Returns (final_assistant_text, updated_history_with_any_tool_turns)
    """
    messages = list(history)

    for _ in range(3):  # allow a couple of tool round-trips, cap to avoid loops
        response = client.models.generate_content(
            model=MODEL,
            contents=messages,
            config=GENERATE_CONFIG,
        )
        candidate = response.candidates[0]

        function_calls = [
            part.function_call
            for part in candidate.content.parts
            if part.function_call
        ]

        if not function_calls:
            final_text = "".join(
                part.text for part in candidate.content.parts if part.text
            )
            messages.append({"role": "model", "parts": candidate.content.parts})
            return final_text, messages

        # Model wants to use a tool: append its turn, run tools, feed results back
        messages.append({"role": "model", "parts": candidate.content.parts})

        function_response_parts = []
        for fc in function_calls:
            result = _execute_tool(fc.name, dict(fc.args))
            function_response_parts.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response={"result": result},
                )
            )
        messages.append({"role": "user", "parts": function_response_parts})

    # Fallback if we somehow looped through tool calls 3 times
    return (
        "Sorry, I'm having a little trouble on my end - let me get a human colleague to help you.",
        messages,
    )