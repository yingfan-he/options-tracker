# Options Trading Tracker

A web application to track options, stocks, and spreads trades with P&L analytics.

## Tech Stack

- **Backend**: FastAPI (Python) + SQLite
- **Frontend**: React + TypeScript + Tailwind CSS
- **Charts**: Recharts
- **State**: TanStack Query (React Query)

## Quick Start (Development)

### Prerequisites
- Python 3.9+
- Node.js 18+

### Run Development Servers

```bash
# Option 1: Use the dev script (runs both backend & frontend)
./run_dev.sh

# Option 2: Run manually
# Terminal 1 - Backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Terminal 2 - Frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

## Deployment to Railway

Railway is the easiest option for deployment.

### One-Click Deploy

1. Push your code to GitHub
2. Go to [railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Railway will auto-detect and deploy

### Manual Setup

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

### Environment Variables (Railway)
No environment variables required - SQLite database is stored locally.

## Deployment to Render

### Option 1: Blueprint (Recommended)

1. Push code to GitHub
2. Go to [render.com](https://render.com)
3. Click "New" → "Blueprint"
4. Connect your GitHub repo
5. Render will use `render.yaml` to configure services

### Option 2: Manual Setup

**Backend Service:**
- Type: Web Service
- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`

**Frontend Service:**
- Type: Static Site
- Build Command: `cd frontend && npm install && npm run build`
- Publish Directory: `frontend/dist`

## Production Build (Self-Hosted)

```bash
# Build frontend
./build.sh

# Run production server
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The backend will serve both the API and the static frontend files.

## API Documentation

When running the backend, visit http://localhost:8000/docs for interactive API documentation (Swagger UI).

## Project Structure

```
options-tracker/
├── backend/
│   ├── main.py           # FastAPI application
│   ├── database.py       # SQLite operations
│   ├── models.py         # Pydantic models
│   └── requirements.txt  # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── pages/        # React pages
│   │   ├── components/   # React components
│   │   ├── api.ts        # API client
│   │   └── types.ts      # TypeScript types
│   └── package.json
├── run_dev.sh           # Development script
├── build.sh             # Production build script
├── railway.json         # Railway config
└── render.yaml          # Render config
```

## Features

- **Dashboard**: P&L summary, premium charts, open positions
- **Trade History**: Filter, sort, pagination, close/expire/assign trades
- **Add Trade**: Options, stocks, spreads with linked trades
- **CSV Import**: Import trades from CSV files with column mapping

## Data Storage

SQLite database stored at `backend/options_tracker.db`. For production deployment, the database persists on the server's filesystem.

**Note**: Railway and Render free tiers may have ephemeral storage. For persistent data, consider:
- Railway: Use a Railway Volume
- Render: Use a Render Disk
- Or: Migrate to PostgreSQL for production
