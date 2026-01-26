"""
Options Trading Tracker - Streamlit App
Supports: Options (calls/puts), Stocks/ETFs, and Spreads.
"""

import streamlit as st
import pandas as pd
from datetime import date, timedelta
from database import (
    init_db, add_trade, get_all_trades, get_open_positions, get_stock_positions,
    get_unique_tickers, calculate_position_pnl, get_pnl_summary,
    get_premium_by_period, delete_trade, insert_sample_data, update_trade_notes,
    update_trade_status
)

st.set_page_config(page_title="Options Tracker", page_icon="📈", layout="wide")
init_db()

st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { padding: 10px 20px; }
</style>
""", unsafe_allow_html=True)

st.title("Options Trading Tracker")

tab_dashboard, tab_trades, tab_add_trade, tab_import = st.tabs(["Dashboard", "All Trades", "Add Trade", "Import CSV"])

# ============== DASHBOARD TAB ==============
with tab_dashboard:
    trades_df = get_all_trades()
    if trades_df.empty:
        st.info("No trades yet. Add your first trade or load sample data.")
        if st.button("Load Sample Data", type="primary"):
            if insert_sample_data():
                st.success("Sample data loaded!")
                st.rerun()
        st.stop()

    summary = get_pnl_summary()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total P&L", f"${summary['total_pnl']:,.2f}")
    with col2:
        st.metric("Realized P&L", f"${summary['realized_pnl']:,.2f}")
    with col3:
        st.metric("Unrealized P&L", f"${summary['unrealized_pnl']:,.2f}")
    with col4:
        st.metric("Total Fees", f"${summary['total_fees']:,.2f}")

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("Premium by Period")
        period = st.selectbox("Group by", ["month", "week", "year"], index=0)
        premium_df = get_premium_by_period(period)

        if not premium_df.empty:
            chart_data = premium_df.copy()
            chart_data['net_after_fees'] = chart_data['net_premium'] - chart_data['total_fees']
            st.bar_chart(chart_data.set_index('period')['net_after_fees'].head(12), use_container_width=True)

            display_df = premium_df.copy()
            display_df.columns = ['Period', 'Net Premium', 'Fees', '# Trades']
            display_df['Net Premium'] = display_df['Net Premium'].apply(lambda x: f"${x:,.2f}")
            display_df['Fees'] = display_df['Fees'].apply(lambda x: f"${x:,.2f}")
            st.dataframe(display_df.head(12), use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("Open Option Positions")
        open_positions = get_open_positions()

        if open_positions.empty:
            st.info("No open option positions")
        else:
            for _, pos in open_positions.iterrows():
                days_to_exp = (pos['expiration_date'].date() - date.today()).days if pd.notna(pos['expiration_date']) else 0
                exp_color = "🔴" if days_to_exp < 0 else "🟡" if days_to_exp <= 7 else "🟢"
                type_icon = "🟢" if pos['option_type'] == 'Call' else "🔴"

                st.markdown(f"""
                **{type_icon} {pos['ticker']}** {pos['option_type']} ${pos['strike_price']:.0f}
                - {pos['action']} {pos['quantity']} @ ${pos['price_per_unit']:.2f}
                - {exp_color} Exp: {pos['expiration_date'].strftime('%m/%d/%y')} ({days_to_exp}d)
                """)
                st.divider()

        # Stock positions
        st.subheader("Stock Positions")
        stock_positions = get_stock_positions()
        if stock_positions.empty:
            st.info("No stock positions")
        else:
            for _, pos in stock_positions.iterrows():
                avg_cost = pos['cost_basis'] / pos['shares'] if pos['shares'] > 0 else 0
                st.markdown(f"**{pos['ticker']}**: {int(pos['shares'])} shares @ ${avg_cost:.2f} avg")

# ============== ALL TRADES TAB ==============
with tab_trades:
    trades_df = get_all_trades()

    if trades_df.empty:
        st.info("No trades recorded yet.")
    else:
        # Trade History
        st.subheader("Trade History")

        # Filters
        col_f1, col_f2, col_f3 = st.columns(3)

        with col_f1:
            tickers = ["All"] + get_unique_tickers()
            selected_ticker = st.selectbox("Ticker", tickers)

        with col_f2:
            asset_types = ["All", "Option", "Stock", "Spread"]
            selected_asset = st.selectbox("Asset Type", asset_types)

        with col_f3:
            actions = ["All", "STO", "BTO", "BTC", "STC", "Buy", "Sell", "Expired", "Assigned"]
            selected_action = st.selectbox("Action", actions)

        # Apply filters
        filtered_df = trades_df.copy()

        if selected_ticker != "All":
            filtered_df = filtered_df[filtered_df['ticker'] == selected_ticker]
        if selected_asset != "All":
            filtered_df = filtered_df[filtered_df['asset_type'] == selected_asset]
        if selected_action != "All":
            filtered_df = filtered_df[filtered_df['action'] == selected_action]

        if not filtered_df.empty:
            # Status comes from database
            filtered_df = filtered_df.copy()
            filtered_df['Status'] = filtered_df['status']

            # Sorting
            sort_col1, sort_col2 = st.columns([2, 1])
            sort_options = {
                'Date (Newest)': ('trade_date', False),
                'Date (Oldest)': ('trade_date', True),
                'Ticker (A-Z)': ('ticker', True),
                'Ticker (Z-A)': ('ticker', False),
                'Strike (Low-High)': ('strike_price', True),
                'Strike (High-Low)': ('strike_price', False),
                'Expiration (Soonest)': ('expiration_date', True),
                'Expiration (Latest)': ('expiration_date', False),
                'Premium (High-Low)': ('price_per_unit', False),
                'Premium (Low-High)': ('price_per_unit', True),
            }
            with sort_col1:
                sort_choice = st.selectbox("Sort by", list(sort_options.keys()), index=0)

            sort_column, ascending = sort_options[sort_choice]
            filtered_df = filtered_df.sort_values(by=sort_column, ascending=ascending, na_position='last')

            # Reset page when sort changes
            if 'last_sort' not in st.session_state or st.session_state.last_sort != sort_choice:
                st.session_state.trade_page = 0
                st.session_state.last_sort = sort_choice

            # Pagination
            rows_per_page = 25
            total_rows = len(filtered_df)
            total_pages = (total_rows + rows_per_page - 1) // rows_per_page

            if 'trade_page' not in st.session_state:
                st.session_state.trade_page = 0

            # Track selected trade for highlighting
            if 'selected_trade_id' not in st.session_state:
                st.session_state.selected_trade_id = None

            # Find linked trade IDs for highlighting
            def get_linked_ids(trade_id):
                if trade_id is None:
                    return set()
                linked = {trade_id}
                # Find trades that link TO this trade
                linking_to = filtered_df[filtered_df['linked_trade_id'] == trade_id]['id'].tolist()
                linked.update(linking_to)
                # Find what this trade links to
                row_data = filtered_df[filtered_df['id'] == trade_id]
                if not row_data.empty:
                    linked_to = row_data.iloc[0].get('linked_trade_id')
                    if pd.notna(linked_to):
                        linked.add(int(linked_to))
                        # Also find siblings (other trades linking to same parent)
                        siblings = filtered_df[filtered_df['linked_trade_id'] == linked_to]['id'].tolist()
                        linked.update(siblings)
                return linked

            highlighted_ids = get_linked_ids(st.session_state.selected_trade_id)

            # Clear selection button
            if st.session_state.selected_trade_id:
                if st.button("Clear Selection", key="clear_highlight"):
                    st.session_state.selected_trade_id = None
                    st.rerun()

            # Header row
            header_cols = st.columns([0.6, 1, 2, 1, 1, 0.5, 0.7, 1.2, 1.8, 1])
            headers = ['ID', 'Date', 'Trade', 'Strike', 'Exp', 'Qty', 'Price', 'Premium/Cost', 'Notes', 'Action']
            for col, header in zip(header_cols, headers):
                col.markdown(f"**{header}**")

            st.divider()

            # Get current page of data
            start_idx = st.session_state.trade_page * rows_per_page
            end_idx = min(start_idx + rows_per_page, total_rows)
            page_df = filtered_df.iloc[start_idx:end_idx]

            # Render each row
            for _, row in page_df.iterrows():
                is_highlighted = row['id'] in highlighted_ids
                highlight_marker = "🔶 " if is_highlighted else ""

                cols = st.columns([0.6, 1, 2, 1, 1, 0.5, 0.7, 1.2, 1.8, 1])

                # Format trade description
                asset = row['asset_type']
                if asset == 'Stock':
                    trade_str = f"📊 {row['action']} {row['ticker']}"
                elif asset == 'Spread':
                    strikes = f"${row['strike_price']:.0f}-${row['strike_price_2']:.0f}" if pd.notna(row['strike_price_2']) else f"${row['strike_price']:.0f}"
                    trade_str = f"📈 {row['ticker']} {row['option_type']} {strikes}"
                else:
                    type_icon = "🟢" if row['option_type'] == 'Call' else "🔴"
                    trade_str = f"{type_icon} {row['action']} {row['option_type']} {row['ticker']}"

                date_str = row['trade_date'].strftime('%m/%d/%y') if pd.notna(row['trade_date']) else '-'
                exp_str = row['expiration_date'].strftime('%m/%d/%y') if pd.notna(row['expiration_date']) else '-'
                strike_str = f"${row['strike_price']:.0f}" if pd.notna(row['strike_price']) else '-'
                price_str = f"${row['price_per_unit']:.2f}"
                notes_str = str(row['notes'])[:25] + "..." if row['notes'] and len(str(row['notes'])) > 25 else (row['notes'] or '-')

                # Calculate Premium/Cost = price × qty × 100 (always)
                # STO, STC, Sell, Expired, Assigned = credit (positive)
                # BTO, BTC, Buy = debit (negative)
                multiplier = 100 if asset in ['Option', 'Spread'] else 1
                if row['action'] in ['STO', 'STC', 'Sell', 'Expired', 'Assigned']:
                    premium_cost = row['price_per_unit'] * row['quantity'] * multiplier
                else:  # BTO, BTC, Buy
                    premium_cost = -row['price_per_unit'] * row['quantity'] * multiplier

                premium_str = f"+{premium_cost:,.2f}" if premium_cost >= 0 else f"{premium_cost:,.2f}"
                premium_color = "green" if premium_cost > 0 else "red" if premium_cost < 0 else ""

                # Clickable ID to select/highlight (with highlight marker)
                with cols[0]:
                    btn_label = f"{highlight_marker}{row['id']}"
                    if st.button(btn_label, key=f"sel_{row['id']}", use_container_width=True):
                        if st.session_state.selected_trade_id == row['id']:
                            st.session_state.selected_trade_id = None
                        else:
                            st.session_state.selected_trade_id = row['id']
                        st.rerun()

                cols[1].markdown(f"{'**' if is_highlighted else ''}{date_str}{'**' if is_highlighted else ''}")
                cols[2].markdown(f"{'**' if is_highlighted else ''}{trade_str}{'**' if is_highlighted else ''}")
                cols[3].markdown(f"{'**' if is_highlighted else ''}{strike_str}{'**' if is_highlighted else ''}")
                cols[4].markdown(f"{'**' if is_highlighted else ''}{exp_str}{'**' if is_highlighted else ''}")
                cols[5].markdown(f"{'**' if is_highlighted else ''}{row['quantity']}{'**' if is_highlighted else ''}")
                cols[6].markdown(f"{'**' if is_highlighted else ''}{price_str}{'**' if is_highlighted else ''}")
                if premium_color:
                    cols[7].markdown(f":{premium_color}[{'**' if is_highlighted else ''}{premium_str}{'**' if is_highlighted else ''}]")
                else:
                    cols[7].markdown(f"{'**' if is_highlighted else ''}{premium_str}{'**' if is_highlighted else ''}")
                cols[8].write(notes_str)

                # Action column - Close button for open positions
                if row['Status'] == 'Open' and row['asset_type'] == 'Option' and row['action'] in ['STO', 'BTO']:
                    with cols[9]:
                        with st.popover("Action", use_container_width=True):
                            close_action = "BTC" if row['action'] == "STO" else "STC"
                            st.markdown(f"**{row['ticker']} {row['option_type']} ${row['strike_price']:.0f}**")

                            action_type = st.radio("Type", ["Close", "Expired", "Assigned"], key=f"action_type_{row['id']}", horizontal=True)

                            if action_type == "Close":
                                close_date = st.date_input("Date", value=date.today(), key=f"hist_close_date_{row['id']}")
                                close_price = st.number_input("Price", min_value=0.0, value=0.0, step=0.01, key=f"hist_close_price_{row['id']}")
                                close_fees = st.number_input("Fees", min_value=0.0, value=0.0, step=0.01, key=f"hist_close_fees_{row['id']}")
                                if st.button(f"Confirm {close_action}", key=f"hist_close_{row['id']}", type="primary"):
                                    exp_date = row['expiration_date'].date() if hasattr(row['expiration_date'], 'date') else row['expiration_date']
                                    # Create closing trade entry
                                    closing_trade_id = add_trade(
                                        ticker=row['ticker'], asset_type='Option', option_type=row['option_type'],
                                        action=close_action, strike_price=float(row['strike_price']),
                                        expiration_date=exp_date, trade_date=close_date,
                                        quantity=int(row['quantity']), price_per_unit=close_price,
                                        fees=close_fees, notes="Closed early", linked_trade_id=int(row['id'])
                                    )
                                    # Mark both trades as closed
                                    update_trade_status(int(row['id']), "Closed")
                                    update_trade_status(closing_trade_id, "Closed")
                                    st.rerun()
                            elif action_type == "Expired":
                                if st.button("Mark Expired", key=f"hist_exp_{row['id']}", type="primary"):
                                    update_trade_status(int(row['id']), "Expired")
                                    st.rerun()
                            else:  # Assigned
                                if st.button("Mark Assigned", key=f"hist_asgn_{row['id']}", type="primary"):
                                    update_trade_status(int(row['id']), "Assigned")
                                    st.rerun()
                else:
                    cols[9].write(row['Status'] if row['Status'] else '-')

            # Pagination controls
            st.divider()
            pg_col1, pg_col2, pg_col3 = st.columns([1, 2, 1])
            with pg_col1:
                if st.button("← Prev", disabled=st.session_state.trade_page == 0):
                    st.session_state.trade_page -= 1
                    st.rerun()
            with pg_col2:
                st.markdown(f"<center>Page {st.session_state.trade_page + 1} of {total_pages} ({total_rows} trades)</center>", unsafe_allow_html=True)
            with pg_col3:
                if st.button("Next →", disabled=st.session_state.trade_page >= total_pages - 1):
                    st.session_state.trade_page += 1
                    st.rerun()

            # Edit notes & Delete - in columns below table
            action_col1, action_col2 = st.columns(2)

            with action_col1:
                with st.expander("Edit Notes"):
                    trade_ids = filtered_df['id'].tolist()
                    edit_id = st.selectbox("Select Trade ID", trade_ids, key="edit_notes_select")

                    selected_trade = filtered_df[filtered_df['id'] == edit_id].iloc[0]
                    current_notes = selected_trade.get('notes', '') or ''

                    new_notes = st.text_area("Notes", value=current_notes, key=f"notes_{edit_id}")
                    if st.button("Save Notes", type="primary"):
                        if update_trade_notes(edit_id, new_notes):
                            st.success("Notes updated!")
                            st.rerun()

            with action_col2:
                with st.expander("Delete a Trade"):
                    trade_ids = filtered_df['id'].tolist()
                    delete_id = st.selectbox("Select Trade ID to Delete", trade_ids)
                    if st.button("Delete Trade", type="secondary"):
                        if delete_trade(delete_id):
                            st.success(f"Trade {delete_id} deleted!")
                            st.rerun()

# ============== ADD TRADE TAB ==============
with tab_add_trade:
    st.subheader("Add New Trade")

    col_main, col_ref = st.columns([2, 1])

    with col_main:
        with st.form("add_trade_form", clear_on_submit=True):
            asset_type = st.selectbox("Asset Type", ["Option", "Stock", "Spread"])

            col1, col2 = st.columns(2)

            with col1:
                ticker = st.text_input("Ticker Symbol", placeholder="AAPL").upper()

                if asset_type == "Option":
                    option_type = st.selectbox("Option Type", ["Call", "Put"])
                    action = st.selectbox("Action", ["STO", "BTO", "BTC", "STC"])
                elif asset_type == "Stock":
                    option_type = None
                    action = st.selectbox("Action", ["Buy", "Sell"])
                else:  # Spread
                    option_type = st.selectbox("Option Type", ["Call", "Put"])
                    action = st.selectbox("Action", ["BTO", "STO", "BTC", "STC"])

                if asset_type in ["Option", "Spread"]:
                    strike_price = st.number_input("Strike Price", min_value=0.01, value=100.00, step=0.50)
                    if asset_type == "Spread":
                        strike_price_2 = st.number_input("Strike Price 2", min_value=0.01, value=110.00, step=0.50)
                    else:
                        strike_price_2 = None
                    expiration_date = st.date_input("Expiration Date", value=date.today() + timedelta(days=30))
                else:
                    strike_price = None
                    strike_price_2 = None
                    expiration_date = None

            with col2:
                trade_date = st.date_input("Trade Date", value=date.today())
                quantity = st.number_input("Quantity (contracts/shares)", min_value=1, value=1, step=1)
                price_per_unit = st.number_input("Price per unit", min_value=0.0, value=0.0, step=0.01,
                                                  help="Premium per contract or price per share")
                fees = st.number_input("Fees", min_value=0.0, value=0.0, step=0.01)

            notes = st.text_area("Notes", placeholder="Optional notes...")

            # Link to existing trade
            linked_trade_id = None
            if asset_type == "Option" and action in ["BTC", "STC"]:
                st.markdown("---")
                st.markdown("**Link to Opening Trade**")
                open_pos = get_open_positions()
                if not open_pos.empty:
                    if ticker:
                        matching = open_pos[open_pos['ticker'] == ticker]
                    else:
                        matching = open_pos
                    if not matching.empty:
                        options = {
                            f"{row['id']}: {row['ticker']} {row['option_type']} ${row['strike_price']:.0f}": row['id']
                            for _, row in matching.iterrows()
                        }
                        selected = st.selectbox("Select Opening Trade", ["None"] + list(options.keys()))
                        if selected != "None":
                            linked_trade_id = options[selected]

            submitted = st.form_submit_button("Add Trade", type="primary", use_container_width=True)

            if submitted:
                if not ticker:
                    st.error("Please enter a ticker symbol")
                else:
                    trade_id = add_trade(
                        ticker=ticker,
                        asset_type=asset_type,
                        action=action,
                        trade_date=trade_date,
                        quantity=quantity,
                        price_per_unit=price_per_unit,
                        option_type=option_type,
                        strike_price=strike_price,
                        strike_price_2=strike_price_2,
                        expiration_date=expiration_date,
                        fees=fees,
                        notes=notes,
                        linked_trade_id=linked_trade_id
                    )
                    st.success(f"Trade added! (ID: {trade_id})")
                    st.rerun()

    with col_ref:
        st.markdown("### Quick Reference")
        st.markdown("""
        **Option Actions:**
        - **STO** - Sell to Open (CC/CSP)
        - **BTO** - Buy to Open (LEAP)
        - **BTC** - Buy to Close
        - **STC** - Sell to Close

        **Stock Actions:**
        - **Buy** / **Sell**

        **Spreads:**
        - Enter net debit/credit as price
        - Use both strike fields
        """)

# ============== IMPORT CSV TAB ==============
with tab_import:
    st.subheader("Import Trades from CSV")

    st.markdown("""
    Upload your CSV file. The importer handles messy data with various formats.
    """)

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("**Preview:**")
            st.dataframe(df.head(10), use_container_width=True)

            cols = ["-- Skip --"] + list(df.columns)

            def find_col(keywords, default=0):
                for i, col in enumerate(cols):
                    if any(kw in col.lower() for kw in keywords):
                        return i
                return default

            st.markdown("---")
            st.markdown("**Map your columns:**")

            col1, col2 = st.columns(2)

            with col1:
                ticker_col = st.selectbox("Ticker column", cols, index=find_col(["option", "ticker", "symbol"]))
                action_col = st.selectbox("Action column", cols, index=find_col(["action"]))
                strike_col = st.selectbox("Strike Price column", cols, index=find_col(["strike"]))
                exp_date_col = st.selectbox("Expiration Date column", cols, index=find_col(["expir", "exp"]))

            with col2:
                trade_date_col = st.selectbox("Trade Date column", cols, index=find_col(["transaction", "trade date", "date"]))
                contracts_col = st.selectbox("Quantity column", cols, index=find_col(["contract", "quantity", "#"]))
                premium_col = st.selectbox("Price column", cols, index=find_col(["price"]))
                expired_col = st.selectbox("Expired? column", cols, index=find_col(["expired"]))
                notes_col = st.selectbox("Notes column", cols, index=find_col(["remark", "note"]))

            if st.button("Import Trades", type="primary"):
                required = [ticker_col, action_col, trade_date_col, contracts_col, premium_col]
                if "-- Skip --" in required:
                    st.error("Please map required columns")
                else:
                    imported = 0
                    skipped = 0
                    errors = []

                    for idx, row in df.iterrows():
                        try:
                            raw_action = str(row[action_col]).lower().strip()
                            ticker = str(row[ticker_col]).upper().strip()

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
                                # Try to parse strike range
                                strike_val = str(row.get(strike_col, "")) if strike_col != "-- Skip --" else ""
                                if "-" in strike_val:
                                    parts = strike_val.replace("$", "").split("-")
                                    strike = float(parts[0])
                                    strike_2 = float(parts[1]) if len(parts) > 1 else None
                                else:
                                    strike = float(strike_val) if strike_val else None
                                    strike_2 = None
                                exp_date = pd.to_datetime(row[exp_date_col]).date() if exp_date_col != "-- Skip --" and pd.notna(row.get(exp_date_col)) else None
                            else:
                                asset_type = "Option"
                                # Parse action + option type
                                action = None
                                option_type = None

                                if "sto" in raw_action or "sell to open" in raw_action or (raw_action.startswith("sell") and "close" not in raw_action):
                                    action = "STO"
                                elif "bto" in raw_action or "buy to open" in raw_action or (raw_action.startswith("buy") and "close" not in raw_action):
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

                                strike = float(row[strike_col]) if strike_col != "-- Skip --" and pd.notna(row.get(strike_col)) else None
                                strike_2 = None
                                exp_date = pd.to_datetime(row[exp_date_col]).date() if exp_date_col != "-- Skip --" and pd.notna(row.get(exp_date_col)) else None

                            # Parse trade date
                            t_date = pd.to_datetime(row[trade_date_col]).date()

                            # Parse numbers
                            qty = int(abs(float(row[contracts_col])))
                            price = abs(float(row[premium_col]))
                            notes = str(row[notes_col]) if notes_col != "-- Skip --" and pd.notna(row.get(notes_col)) else ""

                            # Check expired
                            is_expired = False
                            if expired_col != "-- Skip --":
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

                            # Add expired entry if marked
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

                    if imported > 0:
                        st.success(f"Imported {imported} trades!")
                    if errors:
                        with st.expander(f"Errors ({len(errors)})"):
                            for err in errors[:50]:
                                st.warning(err)

        except Exception as e:
            st.error(f"Error: {str(e)}")

st.divider()
st.caption("Options Trading Tracker | Built with Streamlit")
