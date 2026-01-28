import axios from 'axios';
import type {
  Trade,
  TradeCreate,
  PnLSummary,
  PremiumPeriod,
  OpenPosition,
  StockPosition,
  CloseTradeRequest,
  CSVPreview,
  ImportResult,
} from './types';

const api = axios.create({
  baseURL: '/api',
});

// Trades
export const getTrades = async (filters?: {
  ticker?: string;
  asset_type?: string;
  action?: string;
}): Promise<Trade[]> => {
  const params = new URLSearchParams();
  if (filters?.ticker) params.append('ticker', filters.ticker);
  if (filters?.asset_type) params.append('asset_type', filters.asset_type);
  if (filters?.action) params.append('action', filters.action);
  const { data } = await api.get(`/trades?${params.toString()}`);
  return data;
};

export const getTrade = async (id: number): Promise<Trade> => {
  const { data } = await api.get(`/trades/${id}`);
  return data;
};

export const createTrade = async (trade: TradeCreate): Promise<{ id: number }> => {
  const { data } = await api.post('/trades', trade);
  return data;
};

export const updateTrade = async (
  id: number,
  update: { notes?: string; status?: string }
): Promise<void> => {
  await api.patch(`/trades/${id}`, update);
};

export const deleteTrade = async (id: number): Promise<void> => {
  await api.delete(`/trades/${id}`);
};

export const closeTrade = async (
  id: number,
  request: CloseTradeRequest
): Promise<{ closing_trade_id?: number }> => {
  const { data } = await api.post(`/trades/${id}/close`, request);
  return data;
};

// Dashboard
export const getSummary = async (): Promise<PnLSummary> => {
  const { data } = await api.get('/dashboard/summary');
  return data;
};

export const getPremiumByPeriod = async (
  period: 'week' | 'month' | 'year'
): Promise<PremiumPeriod[]> => {
  const { data } = await api.get(`/dashboard/premium/${period}`);
  return data;
};

// Positions
export const getOpenPositions = async (): Promise<OpenPosition[]> => {
  const { data } = await api.get('/positions/options');
  return data;
};

export const getStockPositions = async (): Promise<StockPosition[]> => {
  const { data } = await api.get('/positions/stocks');
  return data;
};

// Tickers
export const getTickers = async (): Promise<string[]> => {
  const { data } = await api.get('/tickers');
  return data;
};

// Import
export const previewCSV = async (file: File): Promise<CSVPreview> => {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await api.post('/import/preview', formData);
  return data;
};

export const importCSV = async (
  file: File,
  mapping: Record<string, string>
): Promise<ImportResult> => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('mapping', JSON.stringify(mapping));
  const { data } = await api.post('/import/process', formData);
  return data;
};

// Utility
export const loadSampleData = async (): Promise<void> => {
  await api.post('/sample-data');
};
