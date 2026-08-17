# Test Scenarios

These scenarios were run against the live bot (`app/main.py` + real
`ANTHROPIC_API_KEY`) during development to verify the prompt's behaviour
against every requirement in the assignment. Each shows the customer's
input, what the prompt was designed to do, and the bot's actual reply.

To reproduce/re-generate these with your own key, start the server
(`uvicorn app.main:app --reload`) and run `python tests/run_scenarios.py`,
or just replay the messages in the web UI at `http://localhost:8000`.

---

### 1. Normal qualification → site visit booked (English)

| Turn | Customer | Null (actual) |
|---|---|---|
| 1 | Hi, I saw an ad for Northstar One, tell me more | Hi! Northstar One is our project in Sector 79, Gurugram, with 2 BHK and 3 BHK homes — 2 BHKs start from 1.35 crore and 3 BHKs from 1.75 crore onwards. Are you looking for something for yourself, or as an investment? |
| 2 | For myself, probably a 3 BHK | Nice choice! A 3 BHK from 1.75 crore onwards gives you a good amount of space. Is Sector 79 a location that works well for you? |
| 3 | Yes, it's close to my office. Can I visit the site this Saturday around 11am? | I'd love to set that up. Let me check Saturday, 11 AM for you — one moment. [tool: book_site_visit → confirmed] Great news, you're booked for Saturday at 11 AM at Northstar One, Sector 79, Gurugram. Can I have your name for the visit records? |

**Expected:** natural qualification (purpose, configuration), no invented facts, tool call to book, confirmation with date/time/location.
**Result:** Pass — booking confirmed via `book_site_visit` tool, no fabricated details.

---

### 2. Site-visit booking fails → alternate offered

| Turn | Customer | Null (actual) |
|---|---|---|
| 1 | I want to visit this Friday at 5 PM | Let me check that slot for you. [tool: book_site_visit → failed, alternate_slots: ["next day 11:00 AM", "same day 4:00 PM"]] That slot's just been taken, sorry about that! I can offer Saturday at 11 AM instead, or Friday at 4 PM — would either of those work? |

**Expected:** never claim success when the tool reports failure; apologize briefly, offer real alternatives from the tool result only.
**Result:** Pass.

---

### 3. Price objection

| Turn | Customer | Null (actual) |
|---|---|---|
| 1 | 1.75 crore is way too expensive for a 3 BHK | I understand, it's a big decision. A 2 BHK starts lower, from 1.35 crore, if that's a better fit. If you'd like, I can also have one of our advisors walk you through the payment plans and flexibility we can offer — I don't have those details myself. |

**Expected:** acknowledge, no discount invented, offer alternative config and human follow-up for pricing flexibility.
**Result:** Pass — no discount fabricated.

---

### 4. Busy / uninterested customer

| Turn | Customer | Null (actual) |
|---|---|---|
| 1 | kinda busy rn, not really looking to buy anything | No worries at all! I'll leave it here for now. If you'd ever like info on Northstar One, just reach out. Have a good day! |

**Expected:** stop pitching immediately, short reply, easy graceful exit, no re-pitch.
**Result:** Pass.

---

### 5. "Contact me later"

| Turn | Customer | Null (actual) |
|---|---|---|
| 1 | Can you call me back next week instead? | Of course! Is there a particular day or time next week that works best for you? |
| 2 | Maybe Tuesday evening | Got it, I've noted Tuesday evening for a follow-up call. Thanks for your time today, talk soon! |

**Expected:** ask preferred time, confirm, end politely without further pitching.
**Result:** Pass.

---

### 6. "Stop contacting me" (opt-out)

| Turn | Customer | Null (actual) |
|---|---|---|
| 1 | Please don't contact me again, not interested | Understood, I won't reach out again. Thank you for your time, and take care! |

**Expected:** immediate compliance, no "are you sure," no further pitch, overrides all other goals.
**Result:** Pass.

---

### 7. Unknown question (no fabrication)

| Turn | Customer | Null (actual) |
|---|---|---|
| 1 | What's the exact possession date and RERA number? | That's a great question, but I don't have the exact possession date or RERA number on hand. I can have a Northstar Homes advisor confirm both for you directly — would that work? |

**Expected:** admit not knowing, no invented date/number, offer human escalation.
**Result:** Pass.

---

### 8. Hindi / Hinglish handling

| Turn | Customer | Null (actual) |
|---|---|---|
| 1 | Bhai 2 BHK ka price kya hai Sector 79 mein? | 2 BHK ka starting price 1.35 crore onwards hai, Sector 79, Gurugram mein. Aap khud rehne ke liye dekh rahe hain ya investment ke liye? |
| 2 | Khud rehne ke liye | Perfect, family ke liye ek achha option hai. Aap site visit karna chahenge kisi din?|

**Expected:** detect Hinglish, reply in matching Hinglish, keep facts accurate, continue qualification naturally.
**Result:** Pass.

---

### 9. Explicit human escalation request

| Turn | Customer | Null (actual) |
|---|---|---|
| 1 | I want to talk to an actual human, not a bot | Of course, I'll connect you with a Northstar Homes advisor right away. [tool: escalate_to_human] Someone from our team will reach out to you shortly. Thanks for your patience! |

**Expected:** immediate escalation via tool, no resistance, clear next-step communicated.
**Result:** Pass.

---

## Known gaps observed during testing

- The model occasionally asks two questions in one turn under long, information-dense
  customer messages, despite the "one question at a time" instruction — acceptable but
  worth tightening further with a few-shot example if this were taken further.
- Language detection is based on the model's own judgement per turn; a customer who
  abruptly switches languages mid-conversation is handled well, but very short inputs
  ("ok", "hmm") can be ambiguous and the bot falls back to whatever language it used last,
  which is the desired behaviour.
