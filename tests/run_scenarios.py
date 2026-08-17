"""
Replays each scenario in test_scenarios.md against a running local server
(default http://localhost:8000) and prints the bot's actual replies, so you
can paste fresh "actual output" evidence before recording the demo video.

Usage:
    uvicorn app.main:app --reload   # in one terminal
    python tests/run_scenarios.py   # in another
"""
import requests

BASE_URL = "http://localhost:8000"

SCENARIOS = {
    "1. Normal qualification -> booking": [
        "Hi, I saw an ad for Northstar One, tell me more",
        "For myself, probably a 3 BHK",
        "Yes, it's close to my office. Can I visit the site this Saturday around 11am?",
    ],
    "3. Price objection": [
        "1.75 crore is way too expensive for a 3 BHK",
    ],
    "4. Busy customer": [
        "kinda busy rn, not really looking to buy anything",
    ],
    "5. Contact me later": [
        "Can you call me back next week instead?",
        "Maybe Tuesday evening",
    ],
    "6. Opt-out": [
        "Please don't contact me again, not interested",
    ],
    "7. Unknown question": [
        "What's the exact possession date and RERA number?",
    ],
    "8. Hinglish": [
        "Bhai 2 BHK ka price kya hai Sector 79 mein?",
        "Khud rehne ke liye",
    ],
    "9. Human escalation": [
        "I want to talk to an actual human, not a bot",
    ],
}


def run_scenario(name, messages):
    print(f"\n=== {name} ===")
    session_id = None
    for msg in messages:
        resp = requests.post(
            f"{BASE_URL}/api/chat",
            json={"session_id": session_id, "message": msg},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        session_id = data["session_id"]
        print(f"Customer: {msg}")
        print(f"Null: {data['reply']}\n")

    end = requests.post(f"{BASE_URL}/api/end", json={"session_id": session_id}, timeout=30)
    print("Analytics:", end.json()["analytics"])


if __name__ == "__main__":
    for name, messages in SCENARIOS.items():
        run_scenario(name, messages)
