
# ♻️ Wakeru (分ける): Japan Garbage Sorting Assistant

**Nebius x NVIDIA Global AI Hackathon, "Best Apps and Agents" track**

🔗 **Live demo:** https://wakeru-japan.streamlit.app
🎥 **Demo video:** [https://youtu.be/eyfgaBA7jOY]

Wakeru helps foreign residents in Japan sort their garbage correctly. Every city in
Japan sets its own rules, usually published only in Japanese, and small towns often
have no English guide at all. Get it wrong and your trash isn't collected.

Wakeru reads **your own city's rules** (paste the text or upload the PDF) and explains
them in **your language**, then helps you set a reminder for collection day.

## Who it's for
Foreign residents in Japan, especially in small towns and rural areas where the city
publishes its rules only in Japanese.

## Features
| Feature | What it does |
|---|---|
| 🤖 AI rule explainer | Upload a city PDF or paste text. Get a plain-language explanation, a practical tip and a safety note in your language. |
| 🌐 Page translation | The whole interface can be shown in 14 languages. |
| 🔔 Collection reminders | Download an `.ics` calendar file (works with Google, Apple and Outlook, no sign-in). Optional Google Calendar login when run locally. |
| 🔎 Quick item lookup | Instant general guidance for about 35 common items. |
| 🏙️ City guides | Sourced local details for Shinjuku, Osaka and Fukuoka. |
| 🧪 Sample rules | Built-in Japanese and English sample notices for trying the app. |

## How we use Nebius and NVIDIA
All AI calls go through **Nebius Token Factory** (OpenAI-compatible API).

| Task | Model | Platform |
|---|---|---|
| Explains the city's garbage rules (core feature) | **NVIDIA Nemotron**: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` | Nebius Token Factory |
| Translates the page interface | `Qwen/Qwen3-30B-A3B-Instruct-2507` | Nebius Token Factory |

The explainer is instructed not to invent details that aren't in the source text. If the
source is unclear, it says so. Model IDs are case-sensitive.

## Run it locally
```bash
git clone https://github.com/panjalabindumadhav-commits/Wakeru.git
cd Wakeru
pip install -r requirements.txt
```
Add your Nebius API key in **one** of these ways:
- Create a `.env` file: `NEBIUS_API_KEY=your-key-here` (see `.env.example`)
- Or create `.streamlit/secrets.toml`: `NEBIUS_API_KEY = "your-key-here"`

Then run:
```bash
streamlit run app.py
```
Optional: set `NEBIUS_MODEL` or `NEBIUS_TRANSLATION_MODEL` to override the default models.

**Google Calendar (optional, local only):** create an OAuth "Desktop app" client in
Google Cloud, save it as `credentials.json` next to `app.py`, and add your account as a
test user. If your login stops working after about 7 days (Google's limit for apps in
Testing mode), delete `token.json` and sign in again. The `.ics` download always works.

## Deploy (Streamlit Community Cloud)
1. Push this repo to GitHub.
2. On share.streamlit.io, create an app: main file `app.py`.
3. In **Advanced settings → Secrets**, add `NEBIUS_API_KEY = "your-key-here"`.

Secrets files (`.env`, `secrets.toml`, `credentials.json`, `token.json`) are in
`.gitignore` and are never committed.

## Known limitations
- Scanned or image-only PDFs can't be read (no OCR). Paste the text instead.
- Very long documents: only the first 12,000 characters are used.
- Sourced city guides exist for only 3 cities (Shinjuku, Osaka, Fukuoka).
- AI explanations and translations can contain mistakes. Always confirm with your ward office.
- Google Calendar login works only when run locally. The deployed app uses the `.ics` download.
- Wakeru doesn't look up collection days by address.
- Not an official source. Japan has no single national standard and no free public API for all cities' rules.

## Project history (what changed during the Submission Period)
Wakeru existed before this hackathon as a simple Streamlit lookup tool with hardcoded
city and item data and **no AI**. During the Submission Period (Aug 26 to Oct 30, 2026) I added:
- AI rule explanation with NVIDIA Nemotron on Nebius Token Factory
- PDF upload and paste-text input, with sample rules
- Page translation into 14 languages
- Calendar reminders (`.ics` download and optional Google Calendar)
- The City guide tab, a redesigned interface, and public deployment

## License
MIT. See `LICENSE.txt`.
