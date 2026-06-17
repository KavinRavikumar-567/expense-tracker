# 💸 Notion-Style Family & Personal Finance Manager

A premium, minimal, and comprehensive **Family & Personal Finance Manager** built with **React (Vite)**, **FastAPI**, and **Turso (Libsql SQLite Cloud)**. Designed with a clean, Apple/Notion-inspired warm white aesthetic.

---

## ✨ Features

- 🔐 **Secure Multi-User Auth**: Secure sign-up/login with salted SHA-256 password hashing. Sessions are persisted in the browser with complete data isolation using custom request headers.
- 📊 **Dynamic Dashboard**: KPI summary cards, interactive monthly cash flow charts (built with Recharts), and automated smart insights.
- 👥 **Member Profiles**: Toggle between **Bachelor** and **Family** modes. Add family members, track dependencies, and manage incomes.
- 💸 **Ledger Tracker**: Categorized income and expense logging with multi-filter searching, date range filters, and category allocation pie charts.
- 🎯 **Smart Budget Planner**: Set category limits for members or family-wide. Status indicator cards (Safe, Warning, Over limit) with progress bars and comparative actuals-vs-limit charts.
- 🏆 **Savings Goals**: Track milestones, update progress dynamically, and calculate projected completion dates.
- 📈 **Investment Portfolio**: Log mutual funds, stocks, FD, RD, gold, and PPF. Automatically computes compound growth rates (CAGR) and total absolute returns.
- 🛡️ **Insurance Manager**: Keep track of policies, renewal date banners, and rule-based coverage gap notifications.
- 🚨 **Emergency Reserve**: Computes 3x (Bachelor) or 6x (Family) target thresholds, visualizes reserve health, and suggests monthly top-up schedules.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | React 19 + Vite | Fast single-page application styled with raw minimal CSS |
| **Charts** | Recharts | Elegant, responsive vector charts for finance trends |
| **Backend** | FastAPI (Python) | High-performance ASGI framework with Pydantic validations |
| **Database** | Libsql / Turso | SQLite-compatible cloud database for serverless persistence |
| **Deployment**| Vercel | Seamless serverless deployment for client and API |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10+
- Node.js 18+

### 1. Local Development Setup

Clone the repository and install the Python backend requirements:
```bash
pip install -r requirements.txt
```

Run the backend development server:
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Run the React Vite dev server:
```bash
cd frontend
npm install
npm run dev
```

The application proxy redirects `/api/*` from Vite (`http://localhost:5173`) to FastAPI (`http://localhost:8000`).

---

## ☁️ Cloud Deployment (Vercel & Turso)

This app is fully optimized for **Vercel** serverless functions and **Turso** cloud SQLite databases.

### 1. Database Setup (Turso)
1. Register/Login on [Turso](https://turso.tech/).
2. Create a new database (e.g., `finance-tracker`).
3. Copy the **Database URL** (`libsql://...`).
4. Generate and copy an **Auth Token**.

### 2. Deployment on Vercel
1. Push your repository to **GitHub**.
2. Go to Vercel, click **Add New** > **Project** and select your GitHub repo.
3. In the project build configuration, set:
   - **Build Command**: `npm run build`
   - **Output Directory**: `frontend/dist`
4. Add the following **Environment Variables**:
   - `TURSO_DB_URL`: *Your Turso Database URL*
   - `TURSO_AUTH_TOKEN`: *Your Turso Auth Token*
5. Click **Deploy**. Vercel will bundle the React client and host your FastAPI backend as serverless functions.

---

## 📁 Repository Structure

```text
├── api/
│   └── index.py            # Vercel backend serverless entrypoint
├── backend/
│   ├── database.py         # Turso client initialization & schema
│   ├── calculations.py     # CAGR & finance algorithms
│   └── main.py             # FastAPI routing and controllers
├── frontend/
│   ├── src/
│   │   ├── components/     # Dashboard, Ledger, Budget, Goals, etc.
│   │   ├── api.js          # API client wrapper
│   │   ├── App.jsx         # App routing & auth onboarding wizard
│   │   └── index.css       # Clean minimal Notion design system
│   ├── package.json        # Frontend React packages
│   └── vite.config.js      # Vite dev server proxy configurations
├── package.json            # Root builder script for Vercel deployment
├── vercel.json             # Vercel rewrites & serverless mappings
└── requirements.txt        # Python library dependencies
```
