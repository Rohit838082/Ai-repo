# 🚀 Antigravity — AI App Builder

**Describe your app. We build it.**

Antigravity is an AI-powered application builder that takes natural language prompts and generates complete, compilable apps (Web / Android) using the **GLM-5** large language model and a high-performance **C++ Builder Engine** — all running on a free Google Colab GPU instance.

---

## ✨ Features

| Feature | Description |
|---|---|
| 💬 ChatGPT-like UI | Premium glassmorphic React interface |
| 🧠 GLM-5 AI Engine | Open-source LLM loaded locally on Colab GPU |
| ⚡ C++ Builder Engine | Blazing-fast project scaffolding and compilation |
| 📦 One-Click Download | Get a `.zip` of your compiled app |
| 🔐 Auth System | Signup/Login with token-based sessions |
| 💎 Subscription Tiers | Free (50 req/day) and Pro (unlimited) |
| 🛡️ Admin Dashboard | User management, stats, and build logs |
| ☁️ Colab Deployment | Everything runs in Google Colab with a Cloudflare tunnel |
| 🎙️ Voice Input | Describe your app by speaking (Web Speech API) |
| 🤖 Multi-Agent AI | Architect → Coder → Reviewer pipeline for higher quality |
| 📱 APK Generation | Android APK builds via Gradle in Colab |

---

## 🏗️ Architecture

```
┌───────────────────────────────────────────────────────┐
│                 Google Colab (T4 GPU)                  │
│                                                       │
│  ┌──────────┐  ┌───────────────┐  ┌───────────────┐  │
│  │ React UI │←→│ FastAPI Server│←→│ GLM-5 (GPU)   │  │
│  │ (static) │  │               │  │ Multi-Agent   │  │
│  └──────────┘  └──────┬────────┘  └───────────────┘  │
│                       │                               │
│                ┌──────▼────────┐                      │
│                │ C++ Builder   │                      │
│                │ Engine (SSE)  │                      │
│                └───────────────┘                      │
│                       │                               │
│              Cloudflare Tunnel ──→ Public URL          │
└───────────────────────────────────────────────────────┘
```

**Multi-Agent Pipeline:**
```
User Prompt → [Architect Agent] → [Coder Agent] → [Reviewer Agent] → Final Output
```

---

## 🚀 Quick Start (Google Colab)

1. **Push this repo** to your GitHub account.
2. Open `Antigravity_App_Builder.ipynb` in [Google Colab](https://colab.research.google.com).
3. Select **Runtime → Change runtime type → T4 GPU**.
4. Update the `REPO_URL` in the first config cell to your repo.
5. **Run All Cells**. A public URL will be printed in the output.
6. Open the URL → Sign up → Start building!

---

## 📂 Project Structure

```
ai repo/
├── .gitignore
├── README.md
├── requirements.txt
├── setup.sh                        # Environment installer
├── start.py                        # Server + Cloudflare tunnel launcher
├── Antigravity_App_Builder.ipynb   # Colab notebook (run this!)
│
├── backend/
│   ├── __init__.py
│   ├── main.py                     # FastAPI entry + GLM-5 + SSE build
│   ├── database.py                 # SQLite: users, subscriptions, logs
│   ├── agents.py                   # Multi-agent AI (Architect/Coder/Reviewer)
│   └── routes/
│       ├── __init__.py
│       ├── auth.py                 # Signup, Login, Profile, Upgrade
│       └── admin.py                # Stats, Users, Build Logs
│
├── engine/
│   ├── builder.cpp                 # C++ scaffolder/compiler/packager
│   └── Makefile
│
└── frontend/
    ├── index.html
    ├── src/
    │   ├── main.jsx
    │   ├── App.jsx                 # Router + auth guard
    │   ├── index.css               # Design system (CSS variables)
    │   └── components/
    │       ├── Auth/Login.jsx       # Login / Signup
    │       ├── Chat/Chat.jsx        # Main chat + build trigger
    │       ├── Builder/             # BuildPanel.jsx + .css (SSE logs)
    │       ├── Subscription/        # Pricing tiers
    │       ├── Admin/               # Dashboard (Admin.jsx + .css)
    │       └── Voice/               # VoiceInput.jsx + .css
    └── dist/                        # Built static output
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | System health + GPU status |
| `POST` | `/api/chat` | Single-agent GLM-5 inference |
| `POST` | `/api/chat/agents` | Multi-agent pipeline (Architect→Coder→Reviewer) |
| `POST` | `/api/build/stream` | SSE stream from C++ engine (web) |
| `POST` | `/api/build/apk` | SSE stream from C++ engine (Android) |
| `GET` | `/api/download/{file}` | Download build artifact |
| `POST` | `/api/auth/signup` | Create account |
| `POST` | `/api/auth/login` | Sign in |
| `GET` | `/api/auth/me` | Current user profile |
| `POST` | `/api/auth/upgrade` | Upgrade to Pro plan |
| `GET` | `/api/admin/stats` | Dashboard statistics |
| `GET` | `/api/admin/users` | User list |
| `GET` | `/api/admin/logs` | Build log history |

---

## 🛠️ Local Development

```bash
# Frontend
cd frontend && npm install && npm run dev

# Backend (separate terminal)
pip install -r requirements.txt
uvicorn backend.main:app --reload

# C++ Engine
cd engine
curl -L -o json.hpp https://github.com/nlohmann/json/releases/download/v3.11.2/json.hpp
make
```

---

## 📜 License

MIT License — Build freely.
