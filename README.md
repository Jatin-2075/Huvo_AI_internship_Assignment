# Northstar Homes — AI Sales Agent

A FastAPI-based conversational AI sales agent for **Northstar Homes**
(fictional real-estate company), built for the Huvo AI Forward Deployed
Engineer assignment.
youtube link -: https://youtube.com/shorts/HknMc2rAkQ4
- **Part 1 — Prompt**: see [`PROMPT.md`](./PROMPT.md) (also embedded in
  [`app/prompt.py`](./app/prompt.py), which is what the app actually uses).
- **Part 2 — Bot**: FastAPI backend + a single-page chat UI, with
  conversation memory, tool-based site-visit booking (with simulated
  failure), human escalation, and post-conversation analytics generation.
- **Tests**: see [`tests/test_scenarios.md`](./tests/test_scenarios.md).

## How it works

```
Browser (static/index.html)
        │  POST /api/chat {session_id, message}
        ▼
FastAPI (app/main.py)
        │  in-memory session store: conversation history per session_id
        ▼
app/llm.py  → Anthropic Messages API, with SYSTEM_PROMPT + two tools:
              - book_site_visit   (simulated: ~70% success, else failure + alternates)
              - escalate_to_human (simulated: logs a hand-off)
        │
        ▼
POST /api/end {session_id}
        │
        ▼
app/analytics.py → second, separate LLM call with its own narrow prompt
                    that reads the transcript and returns structured JSON
                    (budget, configuration, interest level, site-visit
                    status, follow-up needs, opt-out, etc.)
```

The same system prompt is used for every request — it's written to avoid
markdown/formatting so it reads naturally whether it's rendered as chat
text or spoken by a TTS engine on a voice channel. Voice integration
itself (STT/TTS/telephony) is out of scope for this assignment and isn't
wired up — the prompt and backend response format are simply designed to
be voice-compatible.

## How to run

1. **Clone and install:**
   ```bash
   git clone <this-repo-url>
   cd northstar-bot
   python -m venv venv && source venv/bin/activate   # optional but recommended
   pip install -r requirements.txt
   ```

2. **Configure your API key:**
   ```bash
   cp .env.example .env
   # edit .env and set ANTHROPIC_API_KEY=sk-ant-...
   ```

3. **Run the server:**
   ```bash
   uvicorn app.main:app --reload
   ```

4. **Open the UI:** visit `http://localhost:8000` in your browser and chat
   with Null. Click **"End & Analyze"** to end the conversation and see the
   generated lead analytics.

5. **(Optional) Replay the test scenarios** against your running server and
   print fresh actual-output evidence:
   ```bash
   python tests/run_scenarios.py
   ```

## Example test runs

A few manual conversation flows worth trying against a running server —
these exercise qualification, objection handling, language switching,
booking success/failure, and escalation/opt-out paths.

### Run 1 — happy path (qualification → objection → booking success)

```
Hi, I saw an ad for Northstar One, can you tell me more?
I'm looking for a 3 BHK, budget is around 1.5-2 crore
That's a bit expensive, can you do any discount?
Ok, can I visit the site this Saturday around 11am?
My name is Rohan Mehta
Thanks, that works for me
```

Then click **"End & Analyze"** (or call `/api/end`) to trigger analytics
generation.

- Tests: qualification flow, objection handling (should not invent a
  discount), and a successful booking.

### Run 2 — Hindi/Hinglish + tricky cases

```
Namaste, Northstar One ke baare mein thoda bata sakte ho?
2 BHK ka price kya hai?
Abhi busy hoon, baad mein baat karte hain
Actually can you tell me what the loan interest rate would be?
I want to talk to a real person
```

Then end the conversation.

- Tests: Hindi/Hinglish handling, a busy/uninterested customer and
  "contact later" handling, an out-of-scope question the bot shouldn't
  invent numbers for, and human escalation.

### Run 3 — booking failure + "stop contacting me"

```
I'm interested in a 2 BHK, book me a visit tomorrow evening
```

Keep retrying a date/time until you hit the ~30% simulated failure, to
confirm the bot surfaces the failure and offers alternate slots
gracefully. Then send:

```
Please don't contact me again
```

- Tests: the do-not-contact / opt-out requirement — the bot should end
  gracefully rather than keep pitching.

## Key assumptions

- **No real inventory/CRM system exists.** Site-visit booking and human
  escalation are simulated (`app/llm.py`) via a randomized success/failure
  function and a logging stub, respectively — this is explicitly what the
  assignment asks for ("simulate a site-visit booking").
- **Session storage is in-memory**, keyed by a server-generated
  `session_id` returned to the browser after the first message. This is
  fine for a demo; a production version would use Redis/a DB and proper
  auth instead of a bare UUID.
- **One conversation = one browser session.** There's no login/user
  accounts; refreshing the page starts a new session (the client currently
  doesn't persist `session_id` across reloads — noted as a limitation).
- **Language handling is entirely prompt-driven** — there's no separate
  language-detection library; the model detects and mirrors English/Hindi/
  Hinglish itself, which is generally reliable for this use case.
- **Analytics generation is a second, independent LLM call** rather than
  something the sales-agent prompt itself outputs, so the agent's turns
  stay focused purely on the conversation and the analytics prompt can be
  iterated on independently.

## Known limitations

- No real voice/telephony integration (STT/TTS) — the prompt is written to
  be voice-compatible, but this repo only implements the text-chat surface,
  as the assignment requires.
- Session persistence is in-memory only; restarting the server loses all
  active conversations.
- No authentication/rate-limiting — not intended for production traffic.
- Booking "availability" is randomized rather than backed by a real
  calendar/inventory system.
- The model can occasionally ask more than one question in a single turn
  on dense inputs, despite the prompt's "one question at a time" rule — see
  `tests/test_scenarios.md` for notes from testing.
- No automated unit tests (pytest); verification is via the documented
  conversation scenarios in `tests/test_scenarios.md`, plus
  `tests/run_scenarios.py` to replay them against a live server.

## AI tools used

- Claude (Anthropic) was used to help draft and refine the system prompt,
  scaffold the FastAPI backend, and write this README.
- The bot itself runs on the Anthropic Claude API (`app/llm.py`).

## Project structure

```
northstar-bot/
├── PROMPT.md                  # Part 1 deliverable — the final prompt
├── README.md
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py                 # FastAPI app & routes
│   ├── prompt.py                # SYSTEM_PROMPT constant (source of truth used by the app)
│   ├── llm.py                   # Anthropic API calls + tool definitions/execution
│   ├── analytics.py             # Post-conversation structured analytics
│   └── static/
│       └── index.html           # Chat UI
└── tests/
    ├── test_scenarios.md        # Input / expected behaviour / actual output
    └── run_scenarios.py         # Replays scenarios against a live server
```