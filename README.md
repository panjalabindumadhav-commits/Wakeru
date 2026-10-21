# ♻️ Wakeru (分ける) — Japan Waste Sorting Assistant

**Sort with confidence.** Wakeru helps foreign residents in Japan navigate the
country's famously complicated, ward-by-ward garbage sorting rules — including
people in small towns whose city publishes rules only in Japanese.

**Nebius x NVIDIA Global AI Hackathon — Best Apps and Agents track.**

![License: MIT](https://img.shields.io/badge/License-MIT-green)

## The problem

Japan's waste rules are set **municipality by municipality** (in Tokyo, even
ward by ward). There is no single national standard, and most small cities
publish their garbage guide **only as a Japanese PDF**. Foreign residents
face fines and uncollected trash over rules they can't even read.

## What Wakeru does

| Feature | How it works |
|---|---|
| 🤖 **AI rule explainer** | Upload your city's garbage PDF (or paste text) → **NVIDIA Nemotron** on **Nebius Token Factory** explains the rule in plain language, in **14 selectable languages** — with a waste-reduction tip and a safety note when relevant. |
| 🔔 **Collection reminders** | Save the explained rule to **Google Calendar** (OAuth), or download an **.ics file** that works with any calendar app — no sign-in needed. 30-minute alarm included. |
| 🔎 **Quick item lookup** | Instant answers for ~35 common items (PET bottles, futons, batteries, spray cans...), each with the category and a practical note. |
| 🏙️ **Sourced city guides** | Real, cited local data for Shinjuku, Osaka, and Fukuoka (bag rules, collection patterns, local quirks like Fukuoka's mandatory color-coded bags). |
| 🧪 **Built-in samples** | No PDF handy? Try sample rules (Japanese ward notice, small-town English notice) with one click — great for demos. |

## How we use Nebius & NVIDIA

- **Model:** `nvidia/nvidia-nemotron-3-nano-30b-a3b` (NVIDIA open-source model)
  — served via the OpenAI-compatible **Nebius Token Factory** inference API.
- **Why this model:** fast + cheap per call (important for a tool residents
  would use daily), strong multilingual quality for explaining Japanese
  municipal documents in the user's language.
- The model is held to a strict **"do not invent details"** system prompt —
  if the source document is unclear, Wakeru says so instead of guessing.
- Model id is configurable via `NEBIUS_MODEL` in `.env`.

## Run it locally

```bash
pip install -r requirements.txt

# 1. Create .env from the example and add your Nebius Token Factory key
cp .env.example .env   # then edit .env

# 2. (Optional) Google Calendar integration
#    Download an OAuth "Desktop app" client from Google Cloud Console
#    (enable the Google Calendar API) and save it as credentials.json here.
#    Without it, the .ics download still works.

# 3. Run
streamlit run app.py
```

## Deploying a public demo

Streamlit Community Cloud works: put `NEBIUS_API_KEY` in the app's Secrets
settings. Google OAuth needs extra config on a hosted demo, so the **.ics
download** is the reliable demo path — it needs no credentials at all.

## Honesty note

Japan's garbage rules are set locally and change over time. Wakeru is a
helpful starting point, **not an official source** — always confirm anything
that matters (fines, bag types, collection days) with your city/ward.

## Project history (significantly updated during the Submission Period)

Wakeru existed before the hackathon as a small static lookup app (a hardcoded
item list). During the Submission Period (Aug 26 – Oct 30, 2026) it was
significantly rebuilt:

- Added the **NVIDIA Nemotron + Nebius Token Factory** AI pipeline
  (multilingual PDF/text rule explanation)
- Added **Google Calendar** reminders and the **.ics download** fallback
- Added **14-language selector**, built-in sample rules, scanned-PDF detection
- Restored and expanded the sourced city guides and the item database
- Complete visual redesign (light-green theme, responsive cards)

## License

MIT — see [LICENSE](LICENSE).
