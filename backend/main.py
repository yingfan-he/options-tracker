"""
FastAPI backend for Options Trading Tracker.
"""

import os
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Optional
import pandas as pd
from io import StringIO

from database import (
    init_db, add_trade, get_trade_by_id, get_all_trades, get_open_positions,
    get_stock_positions, get_unique_tickers, get_pnl_summary, get_premium_by_period,
    delete_trade, update_trade_notes, update_trade_status, insert_sample_data
)
from models import (
    TradeCreate, TradeResponse, TradeUpdate, CloseTradeRequest,
    PnLSummary, PremiumPeriod, ImportColumnMapping
)

app = FastAPI(title="Options Trading Tracker API", version="1.0.0")

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database on startup
@app.on_event("startup")
def startup():
    init_db()


# ============== TRADES ENDPOINTS ==============

@app.get("/api/trades", response_model=list[dict])
def list_trades(
    ticker: Optional[str] = None,
    asset_type: Optional[str] = None,
    action: Optional[str] = None
):
    """Get all trades with optional filters."""
    trades = get_all_trades()

    if ticker and ticker != "All":
        trades = [t for t in trades if t['ticker'] == ticker]
    if asset_type and asset_type != "All":
        trades = [t for t in trades if t['asset_type'] == asset_type]
    if action and action != "All":
        trades = [t for t in trades if t['action'] == action]

    # Convert dates to strings for JSON serialization
    for trade in trades:
        if trade.get('trade_date'):
            trade['trade_date'] = str(trade['trade_date'])
        if trade.get('expiration_date'):
            trade['expiration_date'] = str(trade['expiration_date'])
        if trade.get('created_at'):
            trade['created_at'] = str(trade['created_at'])

    return trades


@app.get("/api/trades/{trade_id}")
def get_trade(trade_id: int):
    """Get a single trade by ID."""
    trade = get_trade_by_id(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if trade.get('trade_date'):
        trade['trade_date'] = str(trade['trade_date'])
    if trade.get('expiration_date'):
        trade['expiration_date'] = str(trade['expiration_date'])
    if trade.get('created_at'):
        trade['created_at'] = str(trade['created_at'])

    return trade


@app.post("/api/trades", response_model=dict)
def create_trade(trade: TradeCreate):
    """Create a new trade."""
    trade_id = add_trade(
        ticker=trade.ticker,
        asset_type=trade.asset_type,
        action=trade.action,
        trade_date=trade.trade_date,
        quantity=trade.quantity,
        price_per_unit=trade.price_per_unit,
        option_type=trade.option_type,
        strike_price=trade.strike_price,
        strike_price_2=trade.strike_price_2,
        expiration_date=trade.expiration_date,
        fees=trade.fees,
        notes=trade.notes,
        linked_trade_id=trade.linked_trade_id
    )
    return {"id": trade_id, "message": "Trade created successfully"}


@app.patch("/api/trades/{trade_id}")
def update_trade(trade_id: int, update: TradeUpdate):
    """Update trade notes or status."""
    trade = get_trade_by_id(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if update.notes is not None:
        update_trade_notes(trade_id, update.notes)
    if update.status is not None:
        update_trade_status(trade_id, update.status)

    return {"message": "Trade updated successfully"}


@app.delete("/api/trades/{trade_id}")
def remove_trade(trade_id: int):
    """Delete a trade."""
    if delete_trade(trade_id):
        return {"message": "Trade deleted successfully"}
    raise HTTPException(status_code=404, detail="Trade not found")


@app.post("/api/trades/{trade_id}/close")
def close_trade(trade_id: int, close_request: CloseTradeRequest):
    """Close an open trade (BTC/STC, Expired, or Assigned)."""
    trade = get_trade_by_id(trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")

    if close_request.action_type == "Close":
        close_action = "BTC" if trade['action'] == "STO" else "STC"
        closing_trade_id = add_trade(
            ticker=trade['ticker'],
            asset_type='Option',
            option_type=trade['option_type'],
            action=close_action,
            strike_price=trade['strike_price'],
            expiration_date=trade['expiration_date'],
            trade_date=close_request.close_date,
            quantity=trade['quantity'],
            price_per_unit=close_request.close_price,
            fees=close_request.close_fees,
            notes="Closed position",
            linked_trade_id=trade_id
        )
        update_trade_status(trade_id, "Closed")
        update_trade_status(closing_trade_id, "Closed")
        return {"message": "Trade closed", "closing_trade_id": closing_trade_id}

    elif close_request.action_type == "Expired":
        update_trade_status(trade_id, "Expired")
        return {"message": "Trade marked as expired"}

    elif close_request.action_type == "Assigned":
        update_trade_status(trade_id, "Assigned")
        return {"message": "Trade marked as assigned"}

    raise HTTPException(status_code=400, detail="Invalid action type")


# ============== POSITIONS ENDPOINTS ==============

@app.get("/api/positions/options")
def get_open_option_positions():
    """Get open option positions."""
    positions = get_open_positions()
    for pos in positions:
        if pos.get('trade_date'):
            pos['trade_date'] = str(pos['trade_date'])
        if pos.get('expiration_date'):
            pos['expiration_date'] = str(pos['expiration_date'])
    return positions


@app.get("/api/positions/stocks")
def get_stock_pos():
    """Get stock positions."""
    return get_stock_positions()


# ============== DASHBOARD ENDPOINTS ==============

@app.get("/api/dashboard/summary", response_model=PnLSummary)
def get_summary():
    """Get P&L summary for dashboard."""
    return get_pnl_summary()


@app.get("/api/dashboard/premium/{period}")
def get_premium(period: str = "month"):
    """Get premium by period (week, month, year)."""
    if period not in ["week", "month", "year"]:
        raise HTTPException(status_code=400, detail="Invalid period")
    return get_premium_by_period(period)


@app.get("/api/tickers")
def get_tickers():
    """Get list of unique tickers."""
    return get_unique_tickers()


# ============== IMPORT ENDPOINTS ==============

@app.post("/api/import/preview")
async def preview_csv(file: UploadFile = File(...)):
    """Preview CSV file and return columns and sample data."""
    content = await file.read()
    try:
        df = pd.read_csv(StringIO(content.decode('utf-8')))
        return {
            "columns": list(df.columns),
            "preview": df.head(10).to_dict(orient='records'),
            "row_count": len(df)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")


@app.post("/api/import/process")
async def import_csv(file: UploadFile = File(...), mapping: str = None):
    """Import trades from CSV with column mapping."""
    import json

    content = await file.read()
    try:
        df = pd.read_csv(StringIO(content.decode('utf-8')))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing CSV: {str(e)}")

    if not mapping:
        raise HTTPException(status_code=400, detail="Column mapping required")

    try:
        col_map = json.loads(mapping)
    except:
        raise HTTPException(status_code=400, detail="Invalid mapping JSON")

    imported = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            raw_action = str(row[col_map['action_col']]).lower().strip()
            ticker = str(row[col_map['ticker_col']]).upper().strip()

            # Determine asset type and parse action
            if "stock" in raw_action or "etf" in raw_action:
                asset_type = "Stock"
                action = "Buy" if "buy" in raw_action else "Sell"
                option_type = None
                strike = None
                exp_date = None
            elif "spread" in raw_action or "collar" in raw_action:
                asset_type = "Spread"
                option_type = "Call" if "call" in raw_action else "Put"
                action = "BTO"
                strike_col = col_map.get('strike_col')
                strike_val = str(row.get(strike_col, "")) if strike_col else ""
                if "-" in strike_val:
                    parts = strike_val.replace("$", "").split("-")
                    strike = float(parts[0])
                    strike_2 = float(parts[1]) if len(parts) > 1 else None
                else:
                    strike = float(strike_val) if strike_val else None
                    strike_2 = None
                exp_col = col_map.get('exp_date_col')
                exp_date = pd.to_datetime(row[exp_col]).date() if exp_col and pd.notna(row.get(exp_col)) else None
            else:
                asset_type = "Option"
                action = None
                option_type = None

                if "sto" in raw_action or "sell to open" in raw_action:
                    action = "STO"
                elif "bto" in raw_action or "buy to open" in raw_action:
                    action = "BTO"
                elif "btc" in raw_action or "buy to close" in raw_action:
                    action = "BTC"
                elif "stc" in raw_action or "sell to close" in raw_action:
                    action = "STC"

                if "put" in raw_action:
                    option_type = "Put"
                elif "call" in raw_action or "cc" in raw_action:
                    option_type = "Call"

                if not action or not option_type:
                    errors.append(f"Row {idx+2}: Cannot parse '{raw_action}'")
                    continue

                strike_col = col_map.get('strike_col')
                strike = float(row[strike_col]) if strike_col and pd.notna(row.get(strike_col)) else None
                strike_2 = None
                exp_col = col_map.get('exp_date_col')
                exp_date = pd.to_datetime(row[exp_col]).date() if exp_col and pd.notna(row.get(exp_col)) else None

            # Parse trade date
            t_date = pd.to_datetime(row[col_map['trade_date_col']]).date()

            # Parse numbers
            qty = int(abs(float(row[col_map['quantity_col']])))
            price = abs(float(row[col_map['price_col']]))

            notes_col = col_map.get('notes_col')
            notes = str(row[notes_col]) if notes_col and pd.notna(row.get(notes_col)) else ""

            # Check expired
            is_expired = False
            expired_col = col_map.get('expired_col')
            if expired_col:
                exp_val = str(row.get(expired_col, "")).strip().lower()
                is_expired = exp_val in ["yes", "y", "true", "1", "expired"]

            trade_id = add_trade(
                ticker=ticker,
                asset_type=asset_type,
                action=action,
                trade_date=t_date,
                quantity=qty,
                price_per_unit=price,
                option_type=option_type,
                strike_price=strike,
                strike_price_2=strike_2 if asset_type == "Spread" else None,
                expiration_date=exp_date,
                fees=0,
                notes=notes
            )
            imported += 1

            if is_expired and asset_type == "Option" and action in ["STO", "BTO"]:
                add_trade(
                    ticker=ticker, asset_type="Option", action="Expired",
                    trade_date=exp_date or t_date, quantity=qty, price_per_unit=0,
                    option_type=option_type, strike_price=strike,
                    expiration_date=exp_date, notes="Expired (imported)",
                    linked_trade_id=trade_id
                )

        except Exception as e:
            errors.append(f"Row {idx+2}: {str(e)}")

    return {
        "imported": imported,
        "errors": errors[:50],
        "total_errors": len(errors)
    }


# ============== UTILITY ENDPOINTS ==============

@app.post("/api/sample-data")
def load_sample_data():
    """Load sample data for demonstration."""
    if insert_sample_data():
        return {"message": "Sample data loaded"}
    return {"message": "Data already exists"}


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# ============== STATIC FILE SERVING (Production) ==============

# Check if we have a built frontend to serve
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")

if os.path.exists(STATIC_DIR):
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=os.path.join(STATIC_DIR, "assets")), name="assets")

    # Serve index.html for all non-API routes (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="Not found")

        # Serve index.html for SPA routing
        index_path = os.path.join(STATIC_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        raise HTTPException(status_code=404, detail="Not found")
