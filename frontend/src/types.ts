export interface Trade {
  id: number;
  ticker: string;
  asset_type: 'Option' | 'Stock' | 'Spread';
  option_type: 'Call' | 'Put' | null;
  action: string;
  strike_price: number | null;
  strike_price_2: number | null;
  expiration_date: string | null;
  trade_date: string;
  quantity: number;
  price_per_unit: number;
  fees: number;
  notes: string | null;
  linked_trade_id: number | null;
  status: string | null;
  created_at: string | null;
}

export interface TradeCreate {
  ticker: string;
  asset_type: 'Option' | 'Stock' | 'Spread';
  option_type?: 'Call' | 'Put' | null;
  action: string;
  strike_price?: number | null;
  strike_price_2?: number | null;
  expiration_date?: string | null;
  trade_date: string;
  quantity: number;
  price_per_unit: number;
  fees?: number;
  notes?: string | null;
  linked_trade_id?: number | null;
}

export interface PnLSummary {
  total_pnl: number;
  realized_pnl: number;
  unrealized_pnl: number;
  total_fees: number;
}

export interface PremiumPeriod {
  period: string;
  net_premium: number;
  total_fees: number;
  num_trades: number;
}

export interface OpenPosition {
  id: number;
  ticker: string;
  option_type: 'Call' | 'Put';
  action: string;
  strike_price: number;
  expiration_date: string;
  quantity: number;
  price_per_unit: number;
}

export interface StockPosition {
  ticker: string;
  shares: number;
  cost_basis: number;
}

export interface CloseTradeRequest {
  close_date: string;
  close_price: number;
  close_fees: number;
  action_type: 'Close' | 'Expired' | 'Assigned';
}

export interface CSVPreview {
  columns: string[];
  preview: Record<string, any>[];
  row_count: number;
}

export interface ImportResult {
  imported: number;
  errors: string[];
  total_errors: number;
}
