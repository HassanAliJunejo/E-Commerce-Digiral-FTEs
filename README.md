# 🚀 Digital FTE — E-Commerce Automation System

An AI-powered **Digital Full-Time Employee** system that automates your entire e-commerce sales funnel — from monitoring Instagram comments to sending WhatsApp follow-ups — all without manual effort.

---

## 🧠 What It Does

| Module | Role |
|---|---|
| **Instagram Watcher** | Monitors Instagram notifications for buyer comments in real-time |
| **Master Orchestrator** | Matches leads to inventory, generates AI replies in Hinglish |
| **WhatsApp Poster** | Automatically sends personalized messages to leads via WhatsApp Web |
| **Streamlit Dashboard** | Command center to monitor leads, campaigns, and system health |
| **AI Assistant (RAG)** | Chatbot that helps generate product captions and manage campaigns |

---

## 🏗️ Project Structure

```
DIGITAL FTEs/
├── app.py                        # Streamlit Dashboard (Main UI)
├── run_all.py                    # One-click launcher with auto-restart
├── requirements.txt
├── python_scripts/
│   ├── master_orchestrator.py    # AI lead processing engine
│   ├── instagram_watcher.py      # Instagram comment monitor
│   ├── whatsapp_poster.py        # WhatsApp auto-messenger
│   ├── facebook_watcher.py       # Facebook comment monitor
│   ├── multi_platform_poster.py  # Cross-platform post scheduler
│   ├── social_poster.py          # Social media posting engine
│   ├── database_manager.py       # SQLite DB handler
│   ├── ai_utils.py               # Gemini / OpenAI API wrappers
│   ├── vector_engine.py          # RAG vector search engine
│   ├── stealth_utils.py          # Anti-ban human behavior simulation
│   └── init_sessions.py          # Browser session initializer
├── inventory_db/                 # SQLite databases + product images
├── whatsapp_session/             # WhatsApp browser session
├── instagram_session/            # Instagram browser session
└── logs/                         # System logs & screenshots
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/HassanAliJunejo/E-Commerce-Digiral-FTEs.git
cd E-Commerce-Digiral-FTEs
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Environment Variables
Create a `.env` file in the root directory:
```env
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
```

### 4. Initialize Browser Sessions
Run this once to log in to Instagram and WhatsApp:
```bash
python python_scripts/init_sessions.py
```

---

## 🚀 Running the System

### Option 1: Launch Everything at Once (Recommended)
```bash
python run_all.py
```
This starts all 4 systems with **auto-restart** if any crashes:
- 🖥️ Streamlit Dashboard → `http://localhost:8501`
- 👁️ Instagram Watcher
- 🧠 Master Orchestrator
- 📲 WhatsApp Poster

### Option 2: Run Individually
```bash
# Dashboard only
streamlit run app.py

# Individual scripts
python python_scripts/instagram_watcher.py
python python_scripts/master_orchestrator.py
python python_scripts/whatsapp_poster.py
```

---

## 🔄 How the Sales Funnel Works

```
Instagram Comment
       ↓
Instagram Watcher detects buyer intent (keyword + AI)
       ↓
Lead saved to SQLite DB
       ↓
Master Orchestrator matches product from inventory
       ↓
AI generates personalized Hinglish reply with WhatsApp link
       ↓
WhatsApp Poster sends message automatically
       ↓
Lead marked as "completed" ✅
```

---

## 🛡️ Anti-Ban & Stealth Features

- **Human behavior simulation** — random mouse movements, typing delays
- **Active hours enforcement** — system sleeps outside business hours
- **Random jitter delays** — 45–150 second gaps between actions
- **Quota protection** — keyword-first intent detection before calling AI API
- **Auto-restart** — crashed processes restart automatically via `run_all.py`

---

## 🤖 AI Stack

- **Google Gemini 2.0 Flash** — Intent classification & reply generation
- **OpenAI DALL-E** — Product image generation
- **RAG (Vector Engine)** — Knowledge base search for chatbot context
- **Hinglish replies** — Localized for Pakistani e-commerce market

---

## 📊 Dashboard Features

- **Live Metrics** — Total leads, active campaigns, WhatsApp queue
- **Leads Engine** — Real-time lead table with status tracking
- **Creative Studio** — AI campaign generator with caption drafts
- **Platform Health** — Instagram / Facebook / WhatsApp connection status
- **FTE Assistant** — Floating chatbot for quick campaign creation

---

## 📋 Requirements

- Python 3.9+
- Google Gemini API Key
- OpenAI API Key (optional, for image generation)
- Active Instagram & WhatsApp accounts

---

## ⚠️ Disclaimer

This tool is built for legitimate e-commerce business automation. Use responsibly and in accordance with Instagram's and WhatsApp's Terms of Service.
