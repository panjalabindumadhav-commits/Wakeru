"""
♻️ Wakeru (分ける) — Japan Waste Sorting Helper
Nebius x NVIDIA Global AI Hackathon submission — Best Apps and Agents track.

Wakeru helps foreign residents in Japan sort waste correctly:
  1. 🤖 AI rule explainer — upload your city's garbage PDF (or paste text),
     get a clear explanation IN YOUR LANGUAGE, powered by
     NVIDIA Nemotron on Nebius Token Factory.
  2. 🔔 Collection reminders — save the rule to Google Calendar, or download
     an .ics file (no sign-in needed).
  3. 🔎 Quick item lookup — instant answers for ~35 common items.
  4. 🏙️ Sourced city guides — real, cited local data for Shinjuku / Osaka /
     Fukuoka, because Japan's rules are set ward-by-ward.

HONESTY NOTE: Japan's garbage rules are set municipality by municipality —
there is no single national standard and no free public API covering all of
them. Wakeru combines (a) general guidance that holds true almost everywhere,
(b) real sourced data for a few major cities, and (c) AI explanations of the
user's OWN city documents. It always tells users to confirm with their
ward/city's official guide for anythin g that matters (fines, bag types,
collection days). This app is a helpful starting point, not an authority.

SETUP
  1. pip install -r requirements.txt
  2. Create a .env file in this folder:
       NEBIUS_API_KEY=your-actual-key-here
     (optional) NEBIUS_MODEL=<model id from your Token Factory console>
  3. (Optional, for Google Calendar) Put credentials.json from Google Cloud
     Console (OAuth client, Desktop app) in this folder. Without it, the
     "Download .ics" reminder option still works.
  4. Run:  streamlit run app.py
"""

import os
import uuid
import datetime
import json
import html
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# --- PDF reading ---
from pypdf import PdfReader

# --- Google Calendar (optional — the app works fully without it) ---
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GOOGLE_LIBS_AVAILABLE = True
except ImportError:
    GOOGLE_LIBS_AVAILABLE = False

# ---------------------------------------------------------------------------
# Setup
# ---------------------------------------------------------------------------
load_dotenv()

st.set_page_config(
    page_title="Wakeru - Japan Waste Sorting Assistant",
    page_icon="♻️",
    layout="centered",
)

API_KEY = None
try:
    API_KEY = st.secrets.get("NEBIUS_API_KEY")
except Exception:
    pass
if not API_KEY:
    API_KEY = os.getenv("NEBIUS_API_KEY")
BASE_URL = "https://api.tokenfactory.nebius.com/v1"
# Model IDs are case-sensitive; use the exact ID available to this account.
MODEL = os.getenv("NEBIUS_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
TRANSLATION_MODEL = os.getenv(
    "NEBIUS_TRANSLATION_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507"
)
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
MAX_SOURCE_CHARS = 12000  # keep PDF text inside a sane token budget

client = None
if API_KEY:
    client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=90.0, max_retries=2)

# ---------------------------------------------------------------------------
# Translation helper
# ---------------------------------------------------------------------------
def translate_text_for_ui(text: str, target_language: str) -> str:
    if not text or target_language == "English" or not client:
        return text

    system_prompt = (
        "You are a careful translator for a web app. Translate the text naturally "
        f"into {target_language}. Keep the meaning, tone, and format the same. "
        "Return only the translated text, no commentary."
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text},
        ],
        temperature=0.2,
    )
    translated = response.choices[0].message.content
    return translated.strip() if translated else text


@st.cache_data(show_spinner=False, ttl=86400)
def translate_ui_batch(batch: tuple[str, ...], target_language: str) -> dict[str, str]:
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=TRANSLATION_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"Translate each string naturally into {target_language}. "
                            "Return a JSON object with a 'translations' array in input order. "
                            "Preserve names, numbers, placeholders, Markdown, and emojis."
                        ),
                    },
                    {"role": "user", "content": json.dumps(batch, ensure_ascii=False)},
                ],
                max_tokens=2048,
                temperature=0.2,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise ValueError("Empty translation response")
            translated_batch = json.loads(content).get("translations")
            if not isinstance(translated_batch, list) or len(translated_batch) != len(batch):
                raise ValueError("Incomplete translation response")
            return dict(zip(batch, translated_batch))
        except (json.JSONDecodeError, ValueError):
            if attempt == 1:
                raise


@st.cache_data(show_spinner=False, ttl=86400)
def translate_ui_bundle(texts: tuple[str, ...], target_language: str) -> dict[str, str]:
    if target_language == "English" or not client:
        return {text: text for text in texts}

    batches = [texts[start:start + 10] for start in range(0, len(texts), 10)]
    translations = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [
            executor.submit(translate_ui_batch, batch, target_language)
            for batch in batches
        ]
        for future in as_completed(futures):
            translations.update(future.result())
    return translations


# ---------------------------------------------------------------------------
# Theme — light green, professional with a cute touch
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    :root {
        --ink: #1f3d2b;
        --muted: #5c7264;
        --leaf: #2e6b4f;
        --leaf-soft: #57a773;
        --mint: #e2f3e5;
        --paper: #f4faf3;
        --sun: #f2b04e;
        --blush: #f6c9b3;
    }
    .stApp {
        background-color: #dff3dc !important;
        background-image:
            radial-gradient(circle at 92% 4%, rgba(242, 176, 78, .18), transparent 22rem),
            radial-gradient(circle at 4% 96%, rgba(87, 167, 115, .22), transparent 24rem),
            linear-gradient(150deg, #eaf9eb 0%, #dff1df 42%, #d2ebd6 100%);
        background-attachment: fixed;
        color: var(--ink);
    }
    [data-testid="stAppViewContainer"] {
        background: transparent;
    }
    @media (min-width: 640px) and (max-width: 900px) {
        [data-testid="stAppViewContainer"]:has([data-testid="stSidebar"][style*="width: 300px"]) {
            display: flex !important;
            flex-direction: row !important;
        }
        [data-testid="stAppViewContainer"]:has([data-testid="stSidebar"][style*="width: 300px"]) [data-testid="stMain"] {
            position: relative !important;
            inset: auto !important;
            flex: 1 1 0% !important;
            width: auto !important;
            min-width: 0 !important;
        }
    }
    [data-testid="stHeader"] { background: rgba(246, 251, 243, .8); }
    [data-testid="stSidebar"] { background: #234534; }
    [data-testid="stSidebar"] * { color: #eef7ee; }
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: rgba(255, 255, 255, .12);
        border-color: rgba(255, 255, 255, .28);
    }
    .main .block-container,
    .main .block-container p,
    .main .block-container li,
    .main .block-container label,
    .main .block-container span,
    .main .block-container div,
    .main .block-container h1,
    .main .block-container h2,
    .main .block-container h3,
    .main .block-container h4,
    .main .block-container h5,
    .main .block-container h6,
    .main .block-container strong,
    .main .block-container em,
    .stTabs [data-baseweb="tab-list"] button,
    .stTabs [data-baseweb="tab-list"] button span,
    .stAlert,
    .stAlert p,
    .stAlert div,
    .stWarning,
    .stWarning p,
    .stInfo,
    .stInfo p,
    .stMarkdown,
    .stMarkdown p,
    .stMarkdown div,
    .stMarkdown span,
    [data-testid="stStatusWidget"],
    [data-testid="stStatusWidget"] p,
    [data-testid="stStatusWidget"] span,
    [data-testid="stFileUploaderDropzone"],
    [data-testid="stFileUploaderDropzone"] * ,
    .stTab,
    .stExpander,
    .stExpander * {
        color: #100000 !important;
    }
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {
        background: rgba(255, 255, 255, .72) !important;
        color: #000000 !important;
    }
    .hero {
        padding: 2.4rem 2.6rem 2rem;
        border-radius: 26px;
        background: linear-gradient(120deg, #24543c, #3f8a5f);
        color: white;
        box-shadow: 0 16px 38px rgba(36, 84, 60, .20);
        margin-bottom: 1.4rem;
        position: relative;
        overflow: hidden;
    }
    .hero::after {
        content: "🍃";
        position: absolute;
        right: 1.2rem;
        top: .6rem;
        font-size: 4.5rem;
        opacity: .25;
    }
    .hero-kicker {
        color: #ffe1a6;
        font-size: .78rem;
        font-weight: 800;
        letter-spacing: .14em;
        text-transform: uppercase;
        margin-bottom: .6rem;
    }
    .hero h1 { color: white; margin: 0; font-size: clamp(2.4rem, 7vw, 4.4rem); line-height: .95; }
    .hero p { color: #e6f4e8; font-size: 1.05rem; margin: 1rem 0 0; max-width: 42rem; }
    h2, h3 { color: var(--ink); }
    [data-testid="stTextInput"] > div > div,
    [data-testid="stTextArea"] > div > div,
    [data-testid="stDateInput"] > div > div,
    [data-baseweb="select"] > div {
        border-radius: 14px;
        border: 1px solid #c4d9c6;
        background: rgba(255, 255, 255, .85);
    }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-testid="stTextArea"] div,
    [data-testid="stTextInput"] div,
    [data-baseweb="select"] input,
    [data-baseweb="select"] div,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="input"] input {
        color: #000000 !important;
    }
    /* Fix: Force sidebar headings and labels back to white */
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"],
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] * {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="input"] input {
        background: rgba(255, 255, 255, .92) !important;
    }
    [data-testid="stFileUploaderDropzone"],
    [data-testid="stFileUploaderDropzone"] *,
    [data-testid="stFileUploaderDropzone"] label,
    [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stFileUploaderDropzone"] p,
    [data-testid="stFileUploaderDropzone"] div {
        color: #000000 !important;
    }
    [data-testid="stFileUploaderDropzone"] {
        background: rgba(255, 255, 255, 0.82) !important;
        border: 1px solid #9fbea5 !important;
    }
    [data-testid="stFileUploader"] [data-testid="stWidgetLabel"] *,
    [data-testid="stSelectbox"] [data-testid="stWidgetLabel"] *,
    [data-testid="stDateInput"] [data-testid="stWidgetLabel"] *,
    [data-testid="stTimeInput"] [data-testid="stWidgetLabel"] * {
        color: #000000 !important;
    }
    [data-testid="stRadio"] [data-testid="stWidgetLabel"] *,
    [data-testid="stRadio"] [role="radiogroup"] [data-testid="stMarkdownContainer"] * {
        color: #000000 !important;
    }
    [data-testid="stExpander"] {
        border: 1px solid #cfe2d0;
        border-radius: 16px;
        background: rgba(255, 255, 255, .6);
    }
    .stButton > button {
        border-radius: 999px;
        font-weight: 700;
    }
    [data-testid="stButton"] [data-testid="stBaseButton-secondary"],
    [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] {
        color: #000000 !important;
        background: #ffffff !important;
        border: 1px solid #2e6b4f !important;
    }
    [data-testid="stButton"] [data-testid="stBaseButton-secondary"] *,
    [data-testid="stFileUploader"] [data-testid="stBaseButton-secondary"] * {
        color: #000000 !important;
    }
    .card {
        background: rgba(255, 255, 255, .78);
        border: 1px solid #d7e8d8;
        border-radius: 20px;
        padding: 1.2rem 1.4rem;
        box-shadow: 0 8px 22px rgba(46, 107, 79, .08);
        margin-bottom: 1rem;
    }
    .category-badge {
        display: inline-block; padding: 8px 18px; border-radius: 999px;
        font-weight: 700; font-size: 15px; color: white; margin-bottom: 8px;
        box-shadow: 0 4px 12px rgba(31, 61, 43, .14);
    }
    .burnable { background: #e8963c; }
    .nonburnable { background: #5b6b7a; }
    .recyclable { background: #4a90c4; }
    .pet { background: #2e86ab; }
    .oversized { background: #8b5a83; }
    .hazardous { background: #c1622d; }
    .depends { background: #a8a29e; }
    .disclaimer-box {
        background: #fdf1e3; border-left: 4px solid #e8963c; padding: 14px 18px;
        border-radius: 14px; font-size: 13.5px; margin: 16px 0;
    }
    .ok-box {
        background: #e6f4e8; border-left: 4px solid #57a773; padding: 14px 18px;
        border-radius: 14px; font-size: 13.5px; margin: 16px 0;
    }  
[data-testid="stSidebar"] [data-baseweb="select"] > div,
    [data-testid="stSidebar"] [data-baseweb="select"] div {
        background: #1b3629 !important;
        background-color: #1b3629 !important;
        border-color: rgba(255, 255, 255, 0.28) !important;
    }
    [data-testid="stSidebar"] *,
    [data-testid="stSidebar"] [data-baseweb="select"] *,
    [data-testid="stSidebar"] [data-baseweb="select"] span {
        color: #ffffff !important;
        -webkit-text-fill-color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

target_language = st.session_state.get("page_language", "English")

# ---------------------------------------------------------------------------
# Tier 1: real, sourced city-specific data
# ---------------------------------------------------------------------------
TIER1_CITIES = {
    "shinjuku": {
        "name": "Shinjuku, Tokyo (新宿区)",
        "system": "5 categories: Burnable, Non-burnable/metal-ceramic-glass, Recyclables, Oversized, Hazardous.",
        "burnable_days": "Typically 2x/week (exact days depend on your address — check your ward calendar).",
        "nonburnable_days": "Metal/ceramic/glass collected on a fixed pattern — 1st & 3rd, or 2nd & 4th, week-day of the month depending on your area.",
        "bag_rule": "Any clear or semi-transparent bag is accepted — no designated paid bag required in the 23 wards.",
        "local_notes": [
            "Shinjuku runs a dedicated small-metal (小金属) collection day about once a month, separate from regular non-burnable.",
            "Shinjuku has drop-off boxes at the ward office for small electronics (phones, cameras, game consoles) rather than curbside collection.",
            "Collection continues on most national holidays, pausing only around New Year (roughly Dec 31 – Jan 3).",
        ],
        "source": "City of Shinjuku official waste collection PDF; cross-checked against multiple English-language ward guides (2025-2026).",
    },
    "osaka": {
        "name": "Osaka City (大阪市)",
        "system": "3 main categories (simpler than Tokyo): Burnable, Non-burnable, Recyclable — plus Oversized and Hazardous handled separately.",
        "burnable_days": "Typically Mon & Thu (varies by neighborhood).",
        "nonburnable_days": "Typically 2nd Wednesday of the month.",
        "bag_rule": "No designated paid bag required, similar to Tokyo's 23 wards.",
        "local_notes": [
            "Osaka is generally more flexible with plastics — some plastic packaging can go with burnable rather than needing separate recyclable sorting, unlike stricter wards in Tokyo.",
            "PET bottles are typically collected Tue/Fri, combined with other recyclables in many areas.",
        ],
        "source": "Osaka City resident guides (Apollo Properties Osaka resident guide; YOLO Japan Osaka-specific guide, 2025).",
    },
    "fukuoka": {
        "name": "Fukuoka City (福岡市)",
        "system": "Color-coded bag system — distinctive compared to Tokyo/Osaka.",
        "burnable_days": "Varies by ward within the city — check your specific collection calendar.",
        "nonburnable_days": "Varies by ward.",
        "bag_rule": "Designated colored bags REQUIRED and must be purchased: red for burnable, blue for recyclable, yellow for non-burnable. This is different from Tokyo/Osaka, which don't require paid designated bags.",
        "local_notes": [
            "Because Fukuoka requires paid color-coded bags, using the wrong color or a generic clear bag will likely mean your trash is not collected.",
            "Designated bag packs cost roughly ¥450 per 10 for burnable/non-burnable, ¥220 for recyclable (approximate, confirm current pricing locally).",
        ],
        "source": "Multiple cross-checked English-language expat guides describing Fukuoka's official color-coded bag system (2025-2026); bag pricing should be confirmed directly as prices change.",
    },
}

# ---------------------------------------------------------------------------
# Item database — general guidance, sourced from common patterns across
# multiple municipalities' published English guides. Explicitly flagged where
# city variation is significant.
# ---------------------------------------------------------------------------
ITEMS = {
    "food scraps": {"category": "Burnable", "class": "burnable", "note": "Drain excess liquid first. Most cities collect burnable waste 2-3x/week."},
    "vegetable peels": {"category": "Burnable", "class": "burnable", "note": "Same as other food waste — drain liquid first."},
    "paper towel": {"category": "Burnable", "class": "burnable", "note": "Tissues and paper towels are burnable almost everywhere."},
    "tissue": {"category": "Burnable", "class": "burnable", "note": "Burnable in virtually all municipalities."},
    "small wood": {"category": "Burnable", "class": "burnable", "note": "Chopsticks, small branches, toothpicks — burnable."},
    "clothing": {"category": "Burnable (usually)", "class": "burnable", "note": "Most cities treat clothing as burnable, but some have separate textile recycling drop-off bins — check your city."},
    "leather": {"category": "Burnable (usually)", "class": "burnable", "note": "Small leather goods are usually burnable; large leather furniture may count as oversized."},
    "diaper": {"category": "Burnable", "class": "burnable", "note": "Empty solids into the toilet first if possible, per most city guidelines."},
    "styrofoam": {"category": "Depends on city", "class": "depends", "note": "Clean styrofoam trays are often recyclable; food-soiled styrofoam is usually burnable. City-dependent — check local rules."},

    "glass bottle": {"category": "Recyclable", "class": "recyclable", "note": "Rinse first. Some cities sort by color (clear/brown/other). Remove metal caps (those go non-burnable)."},
    "bottle": {"category": "PET bottles (if plastic)", "class": "pet", "note": "Plastic drink bottles: remove cap and label, rinse, crush — PET is its own stream. Glass bottles: recyclable (rinse, remove cap)."},
    "can": {"category": "Recyclable", "class": "recyclable", "note": "Aluminum and steel cans — rinse and crush if possible."},
    "pet bottle": {"category": "PET recyclable (separate)", "class": "pet", "note": "PET bottles are their own category almost everywhere in Japan. Remove the cap and label (those may go in plastic recyclables), rinse, and crush."},
    "plastic bottle": {"category": "PET recyclable (separate)", "class": "pet", "note": "Same as PET bottle — Japan treats drink/seasoning bottles as their own recycling stream."},
    "plastic wrapper": {"category": "Depends on city", "class": "depends", "note": "Some cities recycle soft plastic packaging separately (marked with a プラ symbol); others treat it as burnable. Check your city — this is one of the most city-dependent items."},
    "cardboard": {"category": "Recyclable", "class": "recyclable", "note": "Flatten and bundle with string. Usually collected on a separate paper-recycling day."},
    "newspaper": {"category": "Recyclable", "class": "recyclable", "note": "Bundle with string, usually a dedicated paper collection day."},

    "ceramic": {"category": "Non-burnable", "class": "nonburnable", "note": "Broken ceramics/pottery. Wrap sharp pieces in paper and label 危険 (kiken/dangerous)."},
    "mirror": {"category": "Non-burnable", "class": "nonburnable", "note": "Wrap broken glass/mirror pieces in paper, label as dangerous."},
    "small metal": {"category": "Non-burnable", "class": "nonburnable", "note": "Pots, pans, cutlery, small tools. Some wards have a dedicated 'small metal' collection day."},
    "light bulb": {"category": "Non-burnable / hazardous", "class": "hazardous", "note": "LED and fluorescent bulbs often need separate hazardous-waste handling — check your city, many require store drop-off instead of curbside."},
    "small appliance": {"category": "Non-burnable (usually)", "class": "nonburnable", "note": "Kettles, toasters — usually non-burnable if small. Larger appliances (fridges, TVs, AC units, washing machines) fall under a separate national recycling law and are NOT collected curbside — search 'kaden recycling law' for disposal."},

    "battery": {"category": "Hazardous — separate collection", "class": "hazardous", "note": "Never put batteries in burnable/non-burnable — they can cause fires in collection trucks. Most cities require a separate, clearly labeled bag or a store drop-off box."},
    "spray can": {"category": "Hazardous — separate collection", "class": "hazardous", "note": "Empty completely first (outdoors, away from flame). Put out separately, often in a labeled transparent bag."},
    "lighter": {"category": "Hazardous — separate collection", "class": "hazardous", "note": "Empty of fuel first. Treated as dangerous waste in most cities — never mix with regular burnable."},

    "furniture": {"category": "Oversized (sodai gomi)", "class": "oversized", "note": "Requires advance booking and a paid sticker in almost every city — you cannot just leave it curbside. Search '[your city] 粗大ごみ' (sodai gomi) to book."},
    "futon": {"category": "Oversized (sodai gomi)", "class": "oversized", "note": "Usually oversized — requires booking and a fee sticker."},
    "bicycle": {"category": "Oversized (sodai gomi)", "class": "oversized", "note": "Requires booking and a fee sticker in most cities."},
    "fridge": {"category": "Home appliance recycling law", "class": "hazardous", "note": "Refrigerators, washing machines, TVs, and air conditioners fall under Japan's Home Appliance Recycling Law — NOT collected curbside. The retailer you bought it from, or the manufacturer, must take it back for a fee."},
    "tv": {"category": "Home appliance recycling law", "class": "hazardous", "note": "Same as fridge — covered by the Home Appliance Recycling Law, not curbside collection."},
    "computer": {"category": "PC recycling program", "class": "hazardous", "note": "PCs fall under a separate manufacturer take-back recycling program (PCリサイクル), not regular curbside collection."},
    "phone": {"category": "Small electronics drop-off", "class": "depends", "note": "Many wards have dedicated small-electronics drop-off boxes at the ward office (mobile phones, cameras, game consoles) rather than curbside collection."},
}

# ---------------------------------------------------------------------------
# AI explanation (NVIDIA Nemotron on Nebius Token Factory)
# ---------------------------------------------------------------------------
def explain_garbage_rule(raw_text: str, language: str) -> str:
    system_prompt = (
        "You are Wakeru, an assistant that helps foreign residents in Japan "
        "understand local garbage disposal rules, including people in small "
        "towns and rural areas whose city may not publish an English guide. "
        "You will be given raw text (possibly in Japanese) describing a "
        f"disposal rule. Respond entirely in {language}, in a "
        "friendly and clear tone, structured as:\n"
        "1. A plain-language explanation of the rule\n"
        "2. One practical tip to reduce this type of waste, if relevant\n"
        "3. A brief safety or caution note, ONLY if genuinely relevant "
        "(e.g. fire risk, fines, contamination risk) — skip this section "
        "entirely if there's nothing important to flag\n"
        "Do not invent details not present in the source text. If the "
        "source text is unclear on a point, say so rather than guessing."
    )
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": raw_text},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def extract_pdf_text(uploaded_file) -> str:
    """Extract text from an uploaded PDF. Raises on corrupt/encrypted files."""
    reader = PdfReader(uploaded_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()


# ---------------------------------------------------------------------------
# Google Calendar (optional) + .ics fallback (always works)
# ---------------------------------------------------------------------------
def get_calendar_service():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists("credentials.json"):
                raise FileNotFoundError(
                    "credentials.json not found. It must be in the same folder "
                    "as this app (see README), or use the .ics download instead."
                )
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token_file:
            token_file.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


def add_calendar_reminder(title, description, date, time_obj, tz):
    service = get_calendar_service()
    start = datetime.datetime.combine(date, time_obj)
    end = start + datetime.timedelta(minutes=30)
    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat(), "timeZone": tz},
        "end": {"dateTime": end.isoformat(), "timeZone": tz},
    }
    created = service.events().insert(calendarId="primary", body=event).execute()
    return created.get("htmlLink")


def _ics_escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;")
                .replace(",", "\\,").replace("\n", "\\n"))


def build_ics(title, description, date, time_obj, tz) -> str:
    """Minimal, widely-compatible VEVENT (works with Google/Apple/Outlook)."""
    start = datetime.datetime.combine(date, time_obj)
    end = start + datetime.timedelta(minutes=30)

    def fmt(dt):
        return dt.strftime("%Y%m%dT%H%M%S")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Wakeru//Japan Waste Helper//EN",
        "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT",
        f"UID:{uuid.uuid4()}@wakeru-app",
        f"DTSTAMP:{fmt(datetime.datetime.now())}",
        f"DTSTART;TZID={tz}:{fmt(start)}",
        f"DTEND;TZID={tz}:{fmt(end)}",
        f"SUMMARY:{_ics_escape(title)}",
        f"DESCRIPTION:{_ics_escape(description)}",
        "BEGIN:VALARM",
        "TRIGGER:-PT30M",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_ics_escape(title)}",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]
    return "\r\n".join(lines)


# ---------------------------------------------------------------------------
# Example rule texts (for the "Try an example" button — great for demos)
# ---------------------------------------------------------------------------
EXAMPLES = {
    "🏙️ Japanese ward rule (burnable)": (
        "可燃ごみの収集は毎週月曜日と木曜日の午前8時30分までです。"
        "ごみは指定の半透明の袋に入れ、区のルールで決められた場所に出してください。"
        "生ごみは水分を切ってから袋に入れてください。"
        "使用済みの電池やライターは可燃ごみに出さないでください。"
    ),
    "🧴 Japanese recycling rule (PET bottles)": (
        "ペットボトルは資源ごみとして毎週火曜日に収集します。"
        "キャップとラベルを外し、中を軽く洗ってから潰して出してください。"
        "キャップとラベルはプラスチック製容器包装として別に集めます。"
    ),
    "🏘️ English small-town notice": (
        "Burnable garbage is collected every Tuesday and Friday morning. "
        "Please put garbage out by 8:00 AM in semi-transparent bags. "
        "Oversized items (sodai gomi) require advance booking at least "
        "one week before collection and a purchased disposal sticker."
    ),
}

LANGUAGES = [
    "English", "日本語", "中文 (简体)", "한국어", "Tiếng Việt", "ภาษาไทย",
    "Bahasa Indonesia", "Tagalog", "हिन्दी", "Português", "Español",
    "Français", "Deutsch", "العربية",
]

TIMEZONES = [
    "Asia/Tokyo", "Asia/Kolkata", "Asia/Shanghai", "Asia/Seoul",
    "Asia/Bangkok", "Asia/Jakarta", "UTC",
    "Europe/London", "Europe/Berlin",
    "America/Los_Angeles", "America/New_York", "America/Sao_Paulo",
]

WARNING_TEXT = (
    "Japan's waste sorting rules are set by each city/ward individually — "
    "there is no single national standard. Wakeru gives real, sourced guidance for a "
    "few major cities, general guidance elsewhere, and AI explanations of your own city "
    "documents. Always double-check your ward's official guide for anything that matters "
    "(fines, required bag types, exact collection days). If in doubt, ask your ward "
    "office or landlord."
)
CATEGORY_GUIDE = """
| Category | Japanese | What it usually means |
|---|---|---|
| 🔥 Burnable | 燃えるごみ (moeru gomi) | Food waste, paper, small wood, most textiles |
| 🔩 Non-burnable | 燃えないごみ (moenai gomi) | Metal, ceramics, glass, small appliances |
| ♻️ Recyclable | 資源ごみ (shigen gomi) | Cans, glass bottles, cardboard, paper |
| 🧴 PET bottles | ペットボトル | Almost always its own separate category |
| 🛋️ Oversized | 粗大ごみ (sodai gomi) | Furniture, bicycles, futons — needs booking + a paid sticker |
| ⚠️ Hazardous | 危険ごみ (kiken gomi) | Batteries, spray cans, lighters — never mix with regular trash |
"""
APPLIANCE_GUIDE = """
These are **not** collected as regular oversized garbage. Japan's **Home
Appliance Recycling Law** requires the retailer or manufacturer to take them
back for a disposal fee. If you bought it in Japan, the store that sold it to
you is usually your first call. If you're not sure, your city's website will
have a page specifically about kaden recycling (家電リサイクル).
"""
WARD_RULES_GUIDE = """
1. Search "[your city or ward name] ごみ分別" (gomi bunbetsu) or "[your city] garbage sorting guide English"
2. Most wards/cities publish an official PDF or app — search "[your city] ゴミ分別アプリ" for one
3. If you live in an apartment, your landlord or building manager often has a printed guide
4. Your city hall or ward office can usually provide an English guide if you ask
5. **Then paste that PDF or text into the AI tab above and get it explained in your language** 🤖
"""
UI_COPY = (
    "Language translator", "Translate page into", "Japan waste guide · 分別 · AI-powered",
    "♻️ Wakeru", "Sort with confidence. Understand your city's garbage rules in your own language, find the right category for everyday waste, and never miss collection day again.",
    "Please read:", WARNING_TEXT, "⚙️ Setup status", "✅ Nebius API key found",
    "Model: {model}", "⚠️ NEBIUS_API_KEY missing",
    "Add your key to `.env` or Streamlit secrets. Free credits: code `NEBIUS-DEVPOST-GLOBAL26` on the Token Factory site.",
    "✅ Google Calendar ready", "ℹ️ Google Calendar optional — the .ics download works without sign-in.",
    "Built for the Nebius x NVIDIA Global AI Hackathon 🚀\n\nAI model: NVIDIA Nemotron · Inference: Nebius Token Factory",
    "🤖 Ask about a rule (AI)", "🔎 Quick item lookup", "🏙️ City guide",
    "Give Wakeru the rule text", "Upload your city's garbage PDF, or paste text (e.g. copied from your city's website).",
    "Upload a PDF", "No PDF handy? Try a sample rule:", "— pick a sample —", "Or paste text here", "Explain this rule ✨",
    "Could not read that PDF ({error}). Try pasting the text instead.",
    "That PDF looks like a scanned image — no text could be extracted. Try copying the text from your city's website and pasting it below instead.",
    "Please upload a PDF or paste some text first.", "AI is not configured — add your NEBIUS_API_KEY to .env or Streamlit secrets.",
    "Note: very long document — using the first {max_chars} characters.", "Reading and explaining...",
    "Something went wrong calling the AI: {error}\n\nIf it says the model was not found, check the model id (NEBIUS_MODEL in .env) matches your Token Factory console exactly.",
    "Set a collection reminder (optional)", "Collection date", "Put out by (time)", "Timezone",
    "How do you want the reminder?", "Add to my Google Calendar", "Download .ics file (works with any calendar app — no sign-in)",
    "Create reminder 🔔", "♻️ Wakeru garbage collection reminder", "Added to your calendar! [Open event]({link})",
    "Could not add to Google Calendar: {error}\n\nTip: the .ics download below works everywhere, no sign-in needed.",
    "⬇️ Download reminder (.ics)", "Open the downloaded file to add it to Google/Apple/Outlook Calendar.",
    "Quick item lookup", "General guidance that holds true in most places — cross-check anything unusual with your city's rules (or use the AI tab with your city's document).",
    "Type an item in English (e.g. 'pet bottle', 'old futon', 'battery')",
    "I don't have specific guidance for \"{query}\" in this quick-reference list. Try the AI tab with your city's rules, or search '[your city] ごみ分別' (gomi bunbetsu) online.",
    "The general categories (almost every city uses these)", CATEGORY_GUIDE,
    "Big appliances (fridge, washing machine, TV, AC) — read this", APPLIANCE_GUIDE,
    "Finding your specific ward/city rules", WARD_RULES_GUIDE,
    "City guide", "Real, sourced local detail for these cities — more cities coming.",
    "City", "General guidance, not specific to any city", "Showing real, sourced guidance for **{city}**.",
    "**System:** {value}", "**Burnable collection:** {value}", "**Non-burnable collection:** {value}",
    "**Bag rule:** {value}", "**Local notes worth knowing:**", "Source: {source}",
    "💡 **Have this city's garbage PDF?** Paste it into the AI tab and get the full rulebook explained in your language.",
    "No city selected — use the quick lookup tab for general guidance, or select a city above for precise, sourced detail.",
    "Built as a hackathon project to help foreign residents in Japan navigate one of the most confusing parts of daily life here. AI: NVIDIA Nemotron via Nebius Token Factory · Not an official source — always confirm anything important with your city/ward.",
)

translation_sources = list(UI_COPY)
for item_name, item_data in ITEMS.items():
    translation_sources.extend((item_name.capitalize(), item_data["category"], item_data["note"]))
for city_data in TIER1_CITIES.values():
    translation_sources.extend((
        city_data["name"], city_data["system"], city_data["burnable_days"],
        city_data["nonburnable_days"], city_data["bag_rule"], city_data["source"],
        *city_data["local_notes"],
    ))
translation_sources.extend(EXAMPLES.keys())
translation_sources.extend(EXAMPLES.values())
translation_sources = tuple(dict.fromkeys(translation_sources))
with st.sidebar:
    st.markdown("### 🌐 Language translator")
    target_language = st.selectbox(
        "Translate page into",
        LANGUAGES,
        index=LANGUAGES.index(target_language) if target_language in LANGUAGES else 0,
        key="page_language",
    )

translation_error = ""
try:
    if target_language != "English" and client:
        with st.spinner("Translating page..."):
            ui_translations = translate_ui_bundle(translation_sources, target_language)
    else:
        ui_translations = translate_ui_bundle(translation_sources, target_language)
except Exception as exc:
    ui_translations = {}
    if getattr(exc, "status_code", None) == 401:
        translation_error = "Nebius rejected the API key (HTTP 401). Check the key in Streamlit secrets or .env."
    else:
        translation_error = f"{type(exc).__name__}: {exc}"
        if API_KEY:
            translation_error = translation_error.replace(API_KEY, "[redacted]")


def tr(text: str) -> str:
    return ui_translations.get(text, text)


with st.sidebar:
    if target_language != "English" and not client:
        st.warning("Page translation needs the Nebius API key to be enabled first.")
    elif translation_error:
        st.error(f"Page translation failed: {translation_error}")

hero_kicker = html.escape(tr("Japan waste guide · 分別 · AI-powered"))
hero_title = html.escape(tr("♻️ Wakeru"))
hero_text = html.escape(tr("Sort with confidence. Understand your city's garbage rules in your own language, find the right category for everyday waste, and never miss collection day again."))
st.markdown(
    '<div class="hero"><div class="hero-kicker">' + hero_kicker + '</div>'
    '<h1>' + hero_title + '</h1><p>' + hero_text + '</p></div>',
    unsafe_allow_html=True,
)
st.markdown(
    '<div class="disclaimer-box"><strong>' + html.escape(tr("Please read:")) + '</strong> '
    + html.escape(tr(WARNING_TEXT)) + '</div>',
    unsafe_allow_html=True,
)
with st.sidebar:
    st.markdown(f"### {tr('⚙️ Setup status')}")
    if client:
        st.success(tr("✅ Nebius API key found"))
        st.caption(tr("Model: {model}").format(model=MODEL))
    else:
        st.error(tr("⚠️ NEBIUS_API_KEY missing"))
        st.caption(tr("Add your key to `.env` or Streamlit secrets. Free credits: code `NEBIUS-DEVPOST-GLOBAL26` on the Token Factory site."))
    st.markdown("---")
    st.caption(tr("Built for the Nebius x NVIDIA Global AI Hackathon 🚀\n\nAI model: NVIDIA Nemotron · Inference: Nebius Token Factory"))

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    tr("🤖 Ask about a rule (AI)"), tr("🔎 Quick item lookup"), tr("🏙️ City guide")
])

# --- TAB 1: AI rule explainer + reminders -----------------------------------
with tab1:
    st.subheader(tr("Give Wakeru the rule text"))
    st.write(tr("Upload your city's garbage PDF, or paste text (e.g. copied from your city's website)."))

    uploaded_pdf = st.file_uploader(tr("Upload a PDF"), type=["pdf"])

    sample_names = list(EXAMPLES)

    def load_sample_rule():
        sample_index = st.session_state["sample_rule_index_v2"]
        if isinstance(sample_index, str):
            try:
                sample_index = int(sample_index)
            except ValueError:
                sample_index = sample_names.index(sample_index) + 1 if sample_index in sample_names else 0
        if sample_index == 0:
            st.session_state["pasted_text"] = ""
        else:
            st.session_state["pasted_text"] = tr(list(EXAMPLES.values())[sample_index - 1])

    sample_index = st.selectbox(
        tr("No PDF handy? Try a sample rule:"),
        options=list(range(len(sample_names) + 1)),
        format_func=lambda index: tr("— pick a sample —") if index == 0 else tr(sample_names[index - 1]),
        key="sample_rule_index_v2",
        on_change=load_sample_rule,
    )
    pasted_text = st.text_area(tr("Or paste text here"), height=140, key="pasted_text")

    if st.button(tr("Explain this rule ✨"), type="primary"):
        raw_text = ""

        if uploaded_pdf is not None:
            try:
                pdf_text = extract_pdf_text(uploaded_pdf)
            except Exception as e:
                pdf_text = ""
                st.error(tr("Could not read that PDF ({error}). Try pasting the text instead.").format(error=e))

            if pdf_text:
                raw_text = pdf_text
                if pasted_text.strip():
                    raw_text += "\n\n" + pasted_text.strip()
            elif not pasted_text.strip():
                st.warning(tr("That PDF looks like a scanned image — no text could be extracted. Try copying the text from your city's website and pasting it below instead."))

        if not raw_text and pasted_text.strip():
            raw_text = pasted_text.strip()

        if not raw_text:
            st.warning(tr("Please upload a PDF or paste some text first."))
        elif not client:
            st.error(tr("AI is not configured — add your NEBIUS_API_KEY to .env or Streamlit secrets."))
        else:
            if len(raw_text) > MAX_SOURCE_CHARS:
                raw_text = raw_text[:MAX_SOURCE_CHARS]
                st.caption(tr("Note: very long document — using the first {max_chars} characters.").format(max_chars=f"{MAX_SOURCE_CHARS:,}"))
            with st.spinner(tr("Reading and explaining...")):
                try:
                    result = explain_garbage_rule(raw_text, target_language)
                    st.session_state["last_explanation"] = result
                except Exception as e:
                    st.error(tr("Something went wrong calling the AI: {error}\n\nIf it says the model was not found, check the model id (NEBIUS_MODEL in .env) matches your Token Factory console exactly.").format(error=e))

    if "last_explanation" in st.session_state:
        st.markdown("---")
        st.markdown(st.session_state["last_explanation"])

        # --- Reminder section ---
        st.markdown("---")
        st.subheader(tr("Set a collection reminder (optional)"))
        col1, col2 = st.columns(2)
        with col1:
            reminder_date = st.date_input(tr("Collection date"), value=datetime.date.today() + datetime.timedelta(days=1))
        with col2:
            reminder_time = st.time_input(tr("Put out by (time)"), value=datetime.time(8, 0))
        reminder_tz = st.selectbox(tr("Timezone"), TIMEZONES, index=0)

        reminder_desc = st.session_state["last_explanation"][:800]

        gcal_ok = GOOGLE_LIBS_AVAILABLE and os.path.exists("credentials.json")
        method_labels = {
            "google": "Add to my Google Calendar",
            "ics": "Download .ics file (works with any calendar app — no sign-in)",
        }
        method_options = ["ics"] + (["google"] if gcal_ok else [])
        method = st.radio(
            tr("How do you want the reminder?"), method_options,
            format_func=lambda value: tr(method_labels[value]),
        )

        if st.button(tr("Create reminder 🔔")):
            title = tr("♻️ Wakeru garbage collection reminder")
            if method == "google":
                try:
                    link = add_calendar_reminder(
                        title=title, description=reminder_desc,
                        date=reminder_date, time_obj=reminder_time, tz=reminder_tz,
                    )
                    st.success(tr("Added to your calendar! [Open event]({link})").format(link=link))
                except Exception as e:
                    st.error(tr("Could not add to Google Calendar: {error}\n\nTip: the .ics download below works everywhere, no sign-in needed.").format(error=e))
            else:
                ics = build_ics(
                    title=title, description=reminder_desc,
                    date=reminder_date, time_obj=reminder_time, tz=reminder_tz,
                )
                st.download_button(
                    tr("⬇️ Download reminder (.ics)"),
                    data=ics,
                    file_name=f"wakeru_reminder_{reminder_date.isoformat()}.ics",
                    mime="text/calendar",
                )
                st.caption(tr("Open the downloaded file to add it to Google/Apple/Outlook Calendar."))

# --- TAB 2: Quick item lookup ------------------------------------------------
with tab2:
    st.subheader(tr("Quick item lookup"))
    st.caption(tr("General guidance that holds true in most places — cross-check anything unusual with your city's rules (or use the AI tab with your city's document)."))
    query = st.text_input(tr("Type an item in English (e.g. 'pet bottle', 'old futon', 'battery')"), "")
    if query:
        q = query.lower().strip()
        matches = [
            (item_key, item_data) for item_key, item_data in ITEMS.items()
            if q in item_key or item_key in q
            or q in tr(item_key.capitalize()).casefold()
            or tr(item_key.capitalize()).casefold() in q
        ]
        if matches:
            for item_name, info in matches:
                st.markdown(f'<span class="category-badge {info["class"]}">{html.escape(tr(info["category"]))}</span>', unsafe_allow_html=True)
                st.markdown(f"**{tr(item_name.capitalize())}**")
                st.write(tr(info["note"]))
                st.markdown("---")
        else:
            st.info(tr("I don't have specific guidance for \"{query}\" in this quick-reference list. Try the AI tab with your city's rules, or search '[your city] ごみ分別' (gomi bunbetsu) online.").format(query=query))

    with st.expander(tr("The general categories (almost every city uses these)")):
        st.markdown(tr(CATEGORY_GUIDE))

    with st.expander(tr("Big appliances (fridge, washing machine, TV, AC) — read this")):
        st.markdown(tr(APPLIANCE_GUIDE))

    with st.expander(tr("Finding your specific ward/city rules")):
        st.markdown(tr(WARD_RULES_GUIDE))

# --- TAB 3: Sourced city guides ----------------------------------------------
with tab3:
    st.subheader(tr("City guide"))
    st.caption(tr("Real, sourced local detail for these cities — more cities coming."))
    city_records = list(TIER1_CITIES.values())
    city_index = st.selectbox(
        tr("City"), options=list(range(len(city_records) + 1)),
        format_func=lambda index: tr("General guidance, not specific to any city") if index == 0 else tr(city_records[index - 1]["name"]),
        key="city_guide_index",
    )

    if city_index:
        city_data = city_records[city_index - 1]
        st.markdown(tr("Showing real, sourced guidance for **{city}**.").format(city=tr(city_data["name"])))
        st.markdown(tr("**System:** {value}").format(value=tr(city_data["system"])))
        st.markdown(tr("**Burnable collection:** {value}").format(value=tr(city_data["burnable_days"])))
        st.markdown(tr("**Non-burnable collection:** {value}").format(value=tr(city_data["nonburnable_days"])))
        st.markdown(tr("**Bag rule:** {value}").format(value=tr(city_data["bag_rule"])))
        st.markdown(tr("**Local notes worth knowing:**"))
        for note in city_data["local_notes"]:
            st.markdown(f"- {tr(note)}")
        st.caption(tr("Source: {source}").format(source=tr(city_data["source"])))
        st.markdown(tr("💡 **Have this city's garbage PDF?** Paste it into the AI tab and get the full rulebook explained in your language."))
    else:
        st.info(tr("No city selected — use the quick lookup tab for general guidance, or select a city above for precise, sourced detail."))

st.markdown("---")
st.caption(tr("Built as a hackathon project to help foreign residents in Japan navigate one of the most confusing parts of daily life here. AI: NVIDIA Nemotron via Nebius Token Factory · Not an official source — always confirm anything important with your city/ward."))
