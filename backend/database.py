"""
Database module for Options Trading Tracker.
Handles SQLite connection, schema creation, and CRUD operations.
"""

import os
import sqlite3
from datetime import date, datetime
from typing import Optional
import pandas as pd

# Use absolute path - database stored in backend folder
DATABASE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "options_tracker.db")


def get_connection():
    """Get a database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DATABASE_PATH, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database schema."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            asset_type TEXT NOT NULL DEFAULT 'Option' CHECK (asset_type IN ('Option', 'Stock', 'Spread')),
            option_type TEXT CHECK (option_type IN ('Call', 'Put', NULL)),
            action TEXT NOT NULL,
            strike_price REAL,
            strike_price_2 REAL,
            expiration_date DATE,
            trade_date DATE NOT NULL,
            underlying_price REAL,
            quantity INTEGER NOT NULL,
            price_per_unit REAL NOT NULL,
            fees REAL DEFAULT 0,
            notes TEXT,
            linked_trade_id INTEGER,
            status TEXT DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (linked_trade_id) REFERENCES trades(id)
        )
    """)

    # Add status column if it doesn't exist (migration for existing databases)
    try:
        cursor.execute("ALTER TABLE trades ADD COLUMN status TEXT DEFAULT 'Open'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    # Index for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON trades(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_trade_date ON trades(trade_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_linked_trade ON trades(linked_trade_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_asset_type ON trades(asset_type)")

    conn.commit()
    conn.close()


def add_trade(
    ticker: str,
    asset_type: str,
    action: str,
    trade_date: date,
    quantity: int,
    price_per_unit: float,
    option_type: Optional[str] = None,
    strike_price: Optional[float] = None,
    strike_price_2: Optional[float] = None,
    expiration_date: Optional[date] = None,
    underlying_price: Optional[float] = None,
    fees: float = 0,
    notes: str = "",
    linked_trade_id: Optional[int] = None
) -> int:
    """Add a new trade and return its ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO trades (
            ticker, asset_type, option_type, action, strike_price, strike_price_2,
            expiration_date, trade_date, underlying_price, quantity, price_per_unit,
            fees, notes, linked_trade_id
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        ticker.upper(), asset_type, option_type, action, strike_price, strike_price_2,
        expiration_date, trade_date, underlying_price, quantity, price_per_unit,
        fees, notes, linked_trade_id
    ))

    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return trade_id


def get_trade_by_id(trade_id: int) -> Optional[dict]:
    """Get a single trade by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def get_all_trades() -> list[dict]:
    """Get all trades as a list of dicts."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            t.id, t.ticker, t.asset_type, t.option_type, t.action,
            t.strike_price, t.strike_price_2, t.expiration_date, t.trade_date,
            t.underlying_price, t.quantity, t.price_per_unit, t.fees, t.notes,
            t.linked_trade_id, COALESCE(t.status, 'Open') as status, t.created_at
        FROM trades t
        ORDER BY t.trade_date DESC, t.id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_open_positions() -> list[dict]:
    """Get option trades that haven't been closed/expired/assigned yet."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM trades t
        WHERE asset_type = 'Option'
        AND action IN ('STO', 'BTO')
        AND (status IS NULL OR status = 'Open')
        ORDER BY expiration_date ASC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_stock_positions() -> list[dict]:
    """Get current stock positions (net of buys and sells)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            ticker,
            SUM(CASE WHEN action = 'Buy' THEN quantity ELSE -quantity END) as shares,
            SUM(CASE WHEN action = 'Buy' THEN quantity * price_per_unit ELSE -quantity * price_per_unit END) as cost_basis
        FROM trades
        WHERE asset_type = 'Stock'
        GROUP BY ticker
        HAVING shares > 0
        ORDER BY ticker
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_unique_tickers() -> list[str]:
    """Get list of unique tickers."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT ticker FROM trades ORDER BY ticker")
    tickers = [row[0] for row in cursor.fetchall()]
    conn.close()
    return tickers


def calculate_position_pnl(opening_trade_id: int) -> dict:
    """Calculate P&L for a position (opening trade + any closing trade)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM trades WHERE id = ?", (opening_trade_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {'pnl': 0, 'status': 'N/A', 'opening_trade': None, 'closing_trade': None}

    opening = dict(row)

    cursor.execute("SELECT * FROM trades WHERE linked_trade_id = ?", (opening_trade_id,))
    closing_row = cursor.fetchone()
    closing = dict(closing_row) if closing_row else None

    conn.close()

    asset_type = opening.get('asset_type', 'Option')

    if asset_type == 'Stock':
        if opening['action'] == 'Buy':
            cost = opening['price_per_unit'] * opening['quantity'] + opening['fees']
            if closing and closing['action'] == 'Sell':
                proceeds = closing['price_per_unit'] * closing['quantity'] - closing['fees']
                return {'pnl': proceeds - cost, 'status': 'Closed', 'opening_trade': opening, 'closing_trade': closing}
            return {'pnl': -cost, 'status': 'Open', 'opening_trade': opening, 'closing_trade': None}
        return {'pnl': 0, 'status': 'N/A', 'opening_trade': opening, 'closing_trade': closing}

    if asset_type == 'Spread':
        multiplier = 100
        net_premium = opening['price_per_unit'] * opening['quantity'] * multiplier
        fees = opening['fees']

        if closing:
            close_premium = closing['price_per_unit'] * closing['quantity'] * multiplier
            fees += closing['fees']
            pnl = net_premium + close_premium - fees
            status = 'Closed'
        else:
            pnl = net_premium - fees
            status = 'Open'

        return {'pnl': pnl, 'status': status, 'opening_trade': opening, 'closing_trade': closing}

    # For options
    multiplier = 100

    if opening['action'] == 'STO':
        credit = opening['price_per_unit'] * opening['quantity'] * multiplier
        fees = opening['fees']

        if closing:
            if closing['action'] == 'BTC':
                debit = closing['price_per_unit'] * closing['quantity'] * multiplier
                fees += closing['fees']
                pnl = credit - debit - fees
                status = 'Closed'
            elif closing['action'] == 'Expired':
                pnl = credit - fees - closing['fees']
                status = 'Expired'
            elif closing['action'] == 'Assigned':
                pnl = credit - fees - closing['fees']
                status = 'Assigned'
            else:
                pnl = credit - fees
                status = 'Unknown'
        else:
            pnl = credit - fees
            status = 'Open'

    elif opening['action'] == 'BTO':
        debit = opening['price_per_unit'] * opening['quantity'] * multiplier
        fees = opening['fees']

        if closing:
            if closing['action'] == 'STC':
                credit = closing['price_per_unit'] * closing['quantity'] * multiplier
                fees += closing['fees']
                pnl = credit - debit - fees
                status = 'Closed'
            elif closing['action'] == 'Expired':
                pnl = -debit - fees - closing['fees']
                status = 'Expired'
            else:
                pnl = -debit - fees
                status = 'Unknown'
        else:
            pnl = -debit - fees
            status = 'Open'
    else:
        pnl = 0
        status = 'N/A'

    return {
        'pnl': pnl,
        'status': status,
        'opening_trade': opening,
        'closing_trade': closing
    }


def get_pnl_summary() -> dict:
    """Get overall P&L summary."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id FROM trades
        WHERE asset_type = 'Option' AND action IN ('STO', 'BTO')
    """)
    option_ids = [row[0] for row in cursor.fetchall()]

    cursor.execute("""
        SELECT id FROM trades
        WHERE asset_type = 'Spread' AND linked_trade_id IS NULL
    """)
    spread_ids = [row[0] for row in cursor.fetchall()]

    conn.close()

    total_realized = 0
    total_unrealized = 0
    total_fees = 0

    for trade_id in option_ids + spread_ids:
        result = calculate_position_pnl(trade_id)
        if result['status'] == 'Open':
            total_unrealized += result['pnl']
        else:
            total_realized += result['pnl']

        if result['opening_trade']:
            total_fees += result['opening_trade']['fees']
        if result['closing_trade']:
            total_fees += result['closing_trade']['fees']

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            SUM(CASE WHEN action = 'Sell' THEN quantity * price_per_unit ELSE -quantity * price_per_unit END) as net,
            SUM(fees) as fees
        FROM trades WHERE asset_type = 'Stock'
    """)
    row = cursor.fetchone()
    if row and row[0]:
        total_realized += row[0]
        total_fees += row[1] or 0
    conn.close()

    return {
        'realized_pnl': total_realized,
        'unrealized_pnl': total_unrealized,
        'total_pnl': total_realized + total_unrealized,
        'total_fees': total_fees
    }


def get_premium_by_period(period: str = 'month') -> list[dict]:
    """Get net premium aggregated by period (options only)."""
    conn = get_connection()

    if period == 'week':
        group_by = "strftime('%Y-W%W', trade_date)"
    elif period == 'month':
        group_by = "strftime('%Y-%m', trade_date)"
    else:
        group_by = "strftime('%Y', trade_date)"

    query = f"""
        SELECT
            {group_by} as period,
            SUM(CASE
                WHEN asset_type = 'Option' AND action IN ('STO', 'STC') THEN price_per_unit * quantity * 100
                WHEN asset_type = 'Option' AND action IN ('BTO', 'BTC') THEN -price_per_unit * quantity * 100
                WHEN asset_type = 'Spread' THEN price_per_unit * quantity * 100
                ELSE 0
            END) as net_premium,
            SUM(fees) as total_fees,
            COUNT(*) as num_trades
        FROM trades
        WHERE asset_type IN ('Option', 'Spread')
        GROUP BY {group_by}
        ORDER BY period DESC
    """

    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_trade(trade_id: int) -> bool:
    """Delete a trade by ID. Returns True if successful."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE trades SET linked_trade_id = NULL WHERE linked_trade_id = ?", (trade_id,))
    cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def update_trade_notes(trade_id: int, notes: str) -> bool:
    """Update notes for a trade."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE trades SET notes = ? WHERE id = ?", (notes, trade_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def update_trade_status(trade_id: int, status: str) -> bool:
    """Update status for a trade (Open, Closed, Expired, Assigned)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE trades SET status = ? WHERE id = ?", (status, trade_id))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def insert_sample_data():
    """Insert sample trades for demonstration."""
    from datetime import timedelta

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM trades")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return False
    conn.close()

    today = date.today()

    add_trade(
        ticker='AAPL', asset_type='Option', option_type='Call', action='STO',
        strike_price=180, expiration_date=today - timedelta(days=30),
        trade_date=today - timedelta(days=45), quantity=1, price_per_unit=3.25,
        fees=0.65, notes='Covered call'
    )
    add_trade(
        ticker='AAPL', asset_type='Option', option_type='Call', action='BTC',
        strike_price=180, expiration_date=today - timedelta(days=30),
        trade_date=today - timedelta(days=32), quantity=1, price_per_unit=0.50,
        fees=0.65, notes='Closed early', linked_trade_id=1
    )

    add_trade(
        ticker='NVDA', asset_type='Stock', action='Buy',
        trade_date=today - timedelta(days=20), quantity=100, price_per_unit=180.00,
        fees=0, notes='Long position'
    )

    add_trade(
        ticker='TSLA', asset_type='Spread', option_type='Call', action='BTO',
        strike_price=440, strike_price_2=450, expiration_date=today + timedelta(days=30),
        trade_date=today - timedelta(days=5), quantity=1, price_per_unit=-4.55,
        fees=1.30, notes='Bull call spread'
    )

    return True
