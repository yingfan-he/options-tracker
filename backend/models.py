"""
Pydantic models for request/response validation.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import date


class TradeBase(BaseModel):
    ticker: str
    asset_type: str  # Option, Stock, Spread
    option_type: Optional[str] = None  # Call, Put
    action: str  # STO, BTO, BTC, STC, Buy, Sell, Expired, Assigned
    strike_price: Optional[float] = None
    strike_price_2: Optional[float] = None
    expiration_date: Optional[date] = None
    trade_date: date
    quantity: int
    price_per_unit: float
    fees: float = 0
    notes: Optional[str] = None
    linked_trade_id: Optional[int] = None


class TradeCreate(TradeBase):
    pass


class TradeResponse(TradeBase):
    id: int
    status: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class TradeUpdate(BaseModel):
    notes: Optional[str] = None
    status: Optional[str] = None


class CloseTradeRequest(BaseModel):
    close_date: date
    close_price: float
    close_fees: float = 0
    action_type: str  # Close, Expired, Assigned


class PnLSummary(BaseModel):
    total_pnl: float
    realized_pnl: float
    unrealized_pnl: float
    total_fees: float


class PremiumPeriod(BaseModel):
    period: str
    net_premium: float
    total_fees: float
    num_trades: int


class ImportColumnMapping(BaseModel):
    ticker_col: str
    action_col: str
    strike_col: Optional[str] = None
    exp_date_col: Optional[str] = None
    trade_date_col: str
    quantity_col: str
    price_col: str
    expired_col: Optional[str] = None
    notes_col: Optional[str] = None
