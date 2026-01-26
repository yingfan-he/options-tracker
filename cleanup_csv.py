"""
CSV Cleanup Script for Options Trading Data
Reads messy CSV and outputs a clean, normalized version.
"""

import pandas as pd
import re
from datetime import datetime

INPUT_FILE = "sell put - Sheet1.csv"
OUTPUT_FILE = "cleaned_trades.csv"

def parse_action(raw_action):
    """Parse messy action string into (asset_type, action, option_type)"""
    raw = str(raw_action).lower().strip()

    # Stock/ETF trades
    if "stock" in raw or "etf" in raw:
        action = "Buy" if "buy" in raw else "Sell"
        return ("Stock", action, None)

    # Spreads
    if "spread" in raw or "collar" in raw:
        opt_type = "Call" if "call" in raw else "Put"
        if "close" in raw or "stc" in raw or "btc" in raw:
            action = "BTC" if "btc" in raw or "buy" in raw else "STC"
        else:
            action = "BTO"
        return ("Spread", action, opt_type)

    # Regular options
    action = None
    opt_type = None

    # Determine action
    if "sto" in raw or "sell to open" in raw:
        action = "STO"
    elif "bto" in raw or "buy to open" in raw:
        action = "BTO"
    elif "btc" in raw or "buy to close" in raw:
        action = "BTC"
    elif "stc" in raw or "sell to close" in raw:
        action = "STC"
    elif raw.startswith("sell") and "close" not in raw:
        action = "STO"
    elif raw.startswith("buy") and "close" not in raw:
        action = "BTO"

    # Determine option type
    if "put" in raw:
        opt_type = "Put"
    elif "call" in raw or "cc" in raw:
        opt_type = "Call"
    elif action:
        # Default: STO usually = Put (CSP), BTO usually = Call (LEAP)
        # Mark with REVIEW in notes
        opt_type = "Put" if action in ["STO", "BTC"] else "Call"

    if action and opt_type:
        return ("Option", action, opt_type)

    return (None, None, None)


def parse_date(date_str, default_year=2025):
    """Parse various date formats, assuming 2025 if year is missing."""
    if pd.isna(date_str) or str(date_str).strip() in ["", "n/a", "N/A"]:
        return None

    date_str = str(date_str).strip()

    # Fix common typos
    date_str = date_str.replace("//", "/")
    date_str = re.sub(r"/312/", "/31/", date_str)  # 10/312/25 -> 10/31/25

    # Try various formats
    formats = [
        "%m/%d/%y",      # 4/17/25
        "%m/%d/%Y",      # 4/17/2025
        "%m/%d",         # 4/17 (no year)
        "%Y-%m-%d",      # 2025-04-17
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # If no year in format, add default year
            if fmt == "%m/%d":
                dt = dt.replace(year=default_year)
            # Fix 2-digit years that got parsed as 19xx
            if dt.year < 2000:
                dt = dt.replace(year=dt.year + 2000)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    return None


def parse_strike(strike_str):
    """Parse strike price, handling ranges like '190-210'."""
    if pd.isna(strike_str) or str(strike_str).strip() in ["", "n/a", "N/A"]:
        return None, None

    strike_str = str(strike_str).strip().replace("$", "").replace(" ", "")

    # Check for range (spread)
    if "-" in strike_str:
        parts = strike_str.split("-")
        try:
            return float(parts[0]), float(parts[1])
        except:
            return None, None

    # Check for "buy call sell put 120" style
    match = re.search(r'(\d+\.?\d*)', strike_str)
    if match:
        return float(match.group(1)), None

    try:
        return float(strike_str), None
    except:
        return None, None


def parse_quantity(qty_str):
    """Parse quantity, handling various formats."""
    if pd.isna(qty_str):
        return 1
    try:
        return int(abs(float(qty_str)))
    except:
        return 1


def parse_price(price_str):
    """Parse price/premium."""
    if pd.isna(price_str):
        return 0.0
    try:
        return abs(float(price_str))
    except:
        return 0.0


def main():
    print(f"Reading {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)

    cleaned_rows = []
    errors = []

    for idx, row in df.iterrows():
        row_num = idx + 2  # Account for header row

        try:
            # Parse action
            raw_action = row.get("action", "")
            asset_type, action, option_type = parse_action(raw_action)

            if not asset_type:
                errors.append(f"Row {row_num}: Cannot parse action '{raw_action}'")
                continue

            # Get ticker
            ticker = str(row.get("option", "")).upper().strip()
            if not ticker or ticker in ["N/A", "NAN", ""]:
                errors.append(f"Row {row_num}: Missing ticker")
                continue

            # Parse dates
            trade_date = parse_date(row.get("Transaction date"))
            exp_date = parse_date(row.get("expire date"))

            if not trade_date:
                errors.append(f"Row {row_num}: Cannot parse trade date '{row.get('Transaction date')}'")
                continue

            # Parse strike
            strike1, strike2 = parse_strike(row.get("strike price"))

            # Parse quantity and price
            quantity = parse_quantity(row.get("# of contract"))
            price = parse_price(row.get("price"))

            # Get notes
            notes = str(row.get("Remarks", "")) if pd.notna(row.get("Remarks")) else ""

            # Check expired status
            expired_val = str(row.get("expired?", "")).lower().strip()
            is_expired = expired_val in ["expired", "yes", "y", "true", "1"]
            is_assigned = "assigned" in expired_val

            # Build cleaned row
            cleaned_row = {
                "trade_date": trade_date,
                "asset_type": asset_type,
                "action": action,
                "option_type": option_type if option_type else "",
                "ticker": ticker,
                "strike_price": strike1 if strike1 else "",
                "strike_price_2": strike2 if strike2 else "",
                "expiration_date": exp_date if exp_date else "",
                "quantity": quantity,
                "price": price,
                "notes": notes,
                "status": "Expired" if is_expired else ("Assigned" if is_assigned else "")
            }

            cleaned_rows.append(cleaned_row)

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")

    # Create output DataFrame
    output_df = pd.DataFrame(cleaned_rows)

    # Sort by trade date
    output_df = output_df.sort_values("trade_date")

    # Save to CSV
    output_df.to_csv(OUTPUT_FILE, index=False)

    print(f"\n✅ Cleaned {len(cleaned_rows)} trades -> {OUTPUT_FILE}")
    print(f"❌ {len(errors)} errors")

    if errors:
        print("\nErrors (first 20):")
        for err in errors[:20]:
            print(f"  - {err}")

    # Print summary
    print(f"\nSummary:")
    print(f"  Options: {len(output_df[output_df['asset_type'] == 'Option'])}")
    print(f"  Stocks:  {len(output_df[output_df['asset_type'] == 'Stock'])}")
    print(f"  Spreads: {len(output_df[output_df['asset_type'] == 'Spread'])}")


if __name__ == "__main__":
    main()
