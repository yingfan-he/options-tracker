import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { getTrades, getTickers, deleteTrade, updateTrade, closeTrade } from '../api';
import type { Trade, CloseTradeRequest } from '../types';
import Spinner from '../components/Spinner';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: '2-digit' });
}

type SortKey = 'trade_date' | 'ticker' | 'strike_price' | 'expiration_date' | 'price_per_unit';

export default function Trades() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({
    ticker: 'All',
    asset_type: 'All',
    action: 'All',
  });
  const [sortKey, setSortKey] = useState<SortKey>('trade_date');
  const [sortAsc, setSortAsc] = useState(false);
  const [page, setPage] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [editNotesId, setEditNotesId] = useState<number | null>(null);
  const [editNotesValue, setEditNotesValue] = useState('');
  const [closeModalTrade, setCloseModalTrade] = useState<Trade | null>(null);
  const [closeForm, setCloseForm] = useState({
    action_type: 'Close' as 'Close' | 'Expired' | 'Assigned',
    close_date: new Date().toISOString().split('T')[0],
    close_price: 0,
    close_fees: 0,
  });
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const showSuccess = (message: string) => {
    setSuccessMessage(message);
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  const rowsPerPage = 25;

  const { data: trades = [], isLoading } = useQuery({
    queryKey: ['trades'],
    queryFn: () => getTrades(),
  });

  const { data: tickers = [] } = useQuery({
    queryKey: ['tickers'],
    queryFn: getTickers,
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTrade,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      showSuccess('Trade deleted successfully');
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, notes }: { id: number; notes: string }) => updateTrade(id, { notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      setEditNotesId(null);
      showSuccess('Notes updated successfully');
    },
  });

  const closeMutation = useMutation({
    mutationFn: ({ id, request }: { id: number; request: CloseTradeRequest }) => closeTrade(id, request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      queryClient.invalidateQueries({ queryKey: ['openPositions'] });
      queryClient.invalidateQueries({ queryKey: ['summary'] });
      setCloseModalTrade(null);
      showSuccess('Trade closed successfully');
    },
  });

  // Filter trades
  let filtered = [...trades];
  if (filters.ticker !== 'All') filtered = filtered.filter((t) => t.ticker === filters.ticker);
  if (filters.asset_type !== 'All') filtered = filtered.filter((t) => t.asset_type === filters.asset_type);
  if (filters.action !== 'All') filtered = filtered.filter((t) => t.action === filters.action);

  // Sort trades
  filtered.sort((a, b) => {
    let aVal = a[sortKey];
    let bVal = b[sortKey];
    if (aVal === null || aVal === undefined) return 1;
    if (bVal === null || bVal === undefined) return -1;
    if (typeof aVal === 'string') aVal = aVal.toLowerCase();
    if (typeof bVal === 'string') bVal = bVal.toLowerCase();
    if (aVal < bVal) return sortAsc ? -1 : 1;
    if (aVal > bVal) return sortAsc ? 1 : -1;
    return 0;
  });

  // Pagination
  const totalPages = Math.ceil(filtered.length / rowsPerPage);
  const pageData = filtered.slice(page * rowsPerPage, (page + 1) * rowsPerPage);

  // Find linked trades for highlighting
  const getLinkedIds = (id: number | null): Set<number> => {
    if (!id) return new Set();
    const linked = new Set<number>([id]);
    const trade = trades.find((t) => t.id === id);
    if (trade?.linked_trade_id) {
      linked.add(trade.linked_trade_id);
      trades.filter((t) => t.linked_trade_id === trade.linked_trade_id).forEach((t) => linked.add(t.id));
    }
    trades.filter((t) => t.linked_trade_id === id).forEach((t) => linked.add(t.id));
    return linked;
  };

  const highlightedIds = getLinkedIds(selectedId);

  const calculatePremiumCost = (trade: Trade): number => {
    const multiplier = trade.asset_type === 'Stock' ? 1 : 100;
    const isCredit = ['STO', 'STC', 'Sell', 'Expired', 'Assigned'].includes(trade.action);
    return (isCredit ? 1 : -1) * trade.price_per_unit * trade.quantity * multiplier;
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
    setPage(0);
  };

  if (isLoading) {
    return <div className="text-center py-12 text-gray-500">Loading trades...</div>;
  }

  if (trades.length === 0) {
    return (
      <div className="text-center py-12">
        <h2 className="text-xl font-semibold text-gray-700 mb-2">No trades recorded yet</h2>
        <p className="text-gray-500">Add your first trade to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Trade History</h1>

      {/* Success Message */}
      {successMessage && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg flex items-center gap-2 animate-fade-in">
          <svg className="w-5 h-5 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          {successMessage}
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <div className="grid grid-cols-1 sm:grid-cols-3 lg:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Ticker</label>
            <select
              value={filters.ticker}
              onChange={(e) => { setFilters({ ...filters, ticker: e.target.value }); setPage(0); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
            >
              <option value="All">All</option>
              {tickers.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Asset Type</label>
            <select
              value={filters.asset_type}
              onChange={(e) => { setFilters({ ...filters, asset_type: e.target.value }); setPage(0); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
            >
              {['All', 'Option', 'Stock', 'Spread'].map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
            <select
              value={filters.action}
              onChange={(e) => { setFilters({ ...filters, action: e.target.value }); setPage(0); }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
            >
              {['All', 'STO', 'BTO', 'BTC', 'STC', 'Buy', 'Sell', 'Expired', 'Assigned'].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Sort By</label>
            <select
              value={`${sortKey}-${sortAsc ? 'asc' : 'desc'}`}
              onChange={(e) => {
                const [key, dir] = e.target.value.split('-');
                setSortKey(key as SortKey);
                setSortAsc(dir === 'asc');
                setPage(0);
              }}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
            >
              <option value="trade_date-desc">Date (Newest)</option>
              <option value="trade_date-asc">Date (Oldest)</option>
              <option value="ticker-asc">Ticker (A-Z)</option>
              <option value="ticker-desc">Ticker (Z-A)</option>
              <option value="strike_price-asc">Strike (Low-High)</option>
              <option value="strike_price-desc">Strike (High-Low)</option>
              <option value="expiration_date-asc">Expiration (Soonest)</option>
              <option value="expiration_date-desc">Expiration (Latest)</option>
              <option value="price_per_unit-desc">Premium (High-Low)</option>
              <option value="price_per_unit-asc">Premium (Low-High)</option>
            </select>
          </div>
          {selectedId && (
            <div className="flex items-end">
              <button
                onClick={() => setSelectedId(null)}
                className="w-full bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200"
              >
                Clear Selection
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Trades Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-600">ID</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 cursor-pointer hover:text-gray-900" onClick={() => handleSort('trade_date')}>Date</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Trade</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 cursor-pointer hover:text-gray-900" onClick={() => handleSort('strike_price')}>Strike</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 cursor-pointer hover:text-gray-900" onClick={() => handleSort('expiration_date')}>Exp</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">Qty</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600 cursor-pointer hover:text-gray-900" onClick={() => handleSort('price_per_unit')}>Price</th>
                <th className="px-4 py-3 text-right font-medium text-gray-600">Premium/Cost</th>
                <th className="px-4 py-3 text-left font-medium text-gray-600">Notes</th>
                <th className="px-4 py-3 text-center font-medium text-gray-600">Action</th>
              </tr>
            </thead>
            <tbody>
              {pageData.map((trade) => {
                const isHighlighted = highlightedIds.has(trade.id);
                const premiumCost = calculatePremiumCost(trade);
                const typeIcon = trade.asset_type === 'Stock' ? '📊' : trade.option_type === 'Call' ? '🟢' : '🔴';
                const tradeStr = trade.asset_type === 'Stock'
                  ? `${trade.action} ${trade.ticker}`
                  : trade.asset_type === 'Spread'
                  ? `${trade.ticker} ${trade.option_type} $${trade.strike_price}-$${trade.strike_price_2}`
                  : `${trade.action} ${trade.option_type} ${trade.ticker}`;

                return (
                  <tr
                    key={trade.id}
                    className={`border-b border-gray-100 hover:bg-gray-50 ${isHighlighted ? 'bg-orange-50' : ''}`}
                  >
                    <td className="px-4 py-3">
                      <button
                        onClick={() => setSelectedId(selectedId === trade.id ? null : trade.id)}
                        className={`font-medium hover:text-blue-600 ${isHighlighted ? 'text-orange-600' : 'text-gray-700'}`}
                      >
                        {isHighlighted && '🔶 '}{trade.id}
                      </button>
                    </td>
                    <td className={`px-4 py-3 ${isHighlighted ? 'font-medium' : ''}`}>{formatDate(trade.trade_date)}</td>
                    <td className={`px-4 py-3 ${isHighlighted ? 'font-medium' : ''}`}>{typeIcon} {tradeStr}</td>
                    <td className={`px-4 py-3 ${isHighlighted ? 'font-medium' : ''}`}>
                      {trade.strike_price ? `$${trade.strike_price}` : '-'}
                    </td>
                    <td className={`px-4 py-3 ${isHighlighted ? 'font-medium' : ''}`}>{formatDate(trade.expiration_date)}</td>
                    <td className={`px-4 py-3 text-center ${isHighlighted ? 'font-medium' : ''}`}>{trade.quantity}</td>
                    <td className={`px-4 py-3 text-right ${isHighlighted ? 'font-medium' : ''}`}>${trade.price_per_unit.toFixed(2)}</td>
                    <td className={`px-4 py-3 text-right ${premiumCost >= 0 ? 'text-green-600' : 'text-red-600'} ${isHighlighted ? 'font-medium' : ''}`}>
                      {premiumCost >= 0 ? '+' : ''}{formatCurrency(premiumCost)}
                    </td>
                    <td className="px-4 py-3 max-w-[150px] truncate text-gray-600" title={trade.notes || ''}>
                      {trade.notes ? (trade.notes.length > 20 ? trade.notes.slice(0, 20) + '...' : trade.notes) : '-'}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-center gap-2">
                        {trade.status === 'Open' && trade.asset_type === 'Option' && ['STO', 'BTO'].includes(trade.action) ? (
                          <button
                            onClick={() => setCloseModalTrade(trade)}
                            className="text-blue-600 hover:text-blue-800 font-medium text-sm"
                          >
                            Close
                          </button>
                        ) : (
                          <span className="text-gray-500 text-sm">{trade.status || '-'}</span>
                        )}
                        <button
                          onClick={() => {
                            if (confirm(`Delete trade #${trade.id}?`)) {
                              deleteMutation.mutate(trade.id);
                            }
                          }}
                          disabled={deleteMutation.isPending}
                          className="text-red-500 hover:text-red-700 p-1 rounded hover:bg-red-50 transition-colors disabled:opacity-50"
                          title="Delete trade"
                        >
                          {deleteMutation.isPending ? (
                            <Spinner size="sm" />
                          ) : (
                            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                            </svg>
                          )}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="px-4 py-3 border-t border-gray-200 flex items-center justify-between">
          <button
            onClick={() => setPage(page - 1)}
            disabled={page === 0}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ← Prev
          </button>
          <span className="text-sm text-gray-600">
            Page {page + 1} of {totalPages} ({filtered.length} trades)
          </span>
          <button
            onClick={() => setPage(page + 1)}
            disabled={page >= totalPages - 1}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next →
          </button>
        </div>
      </div>

      {/* Edit Notes */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 max-w-md">
        <h3 className="font-semibold text-gray-900 mb-4">Edit Notes</h3>
        <div className="space-y-4">
          <select
            value={editNotesId || ''}
            onChange={(e) => {
              const id = e.target.value ? parseInt(e.target.value) : null;
              setEditNotesId(id);
              const trade = trades.find((t) => t.id === id);
              setEditNotesValue(trade?.notes || '');
            }}
            className="w-full border border-gray-300 rounded-lg px-3 py-2"
          >
            <option value="">Select Trade ID</option>
            {filtered.map((t) => <option key={t.id} value={t.id}>{t.id} - {t.ticker} {t.action}</option>)}
          </select>
          {editNotesId && (
            <>
              <textarea
                value={editNotesValue}
                onChange={(e) => setEditNotesValue(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 h-24"
                placeholder="Enter notes..."
              />
              <button
                onClick={() => updateMutation.mutate({ id: editNotesId, notes: editNotesValue })}
                disabled={updateMutation.isPending}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {updateMutation.isPending ? (
                  <>
                    <Spinner size="sm" />
                    Saving...
                  </>
                ) : (
                  'Save Notes'
                )}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Close Trade Modal */}
      {closeModalTrade && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">
              Close Position: {closeModalTrade.ticker} {closeModalTrade.option_type} ${closeModalTrade.strike_price}
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Action Type</label>
                <div className="flex gap-2">
                  {(['Close', 'Expired', 'Assigned'] as const).map((type) => (
                    <button
                      key={type}
                      onClick={() => setCloseForm({ ...closeForm, action_type: type })}
                      className={`px-4 py-2 rounded-lg text-sm font-medium ${
                        closeForm.action_type === type
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              {closeForm.action_type === 'Close' && (
                <>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Close Date</label>
                    <input
                      type="date"
                      value={closeForm.close_date}
                      onChange={(e) => setCloseForm({ ...closeForm, close_date: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Close Price</label>
                    <input
                      type="number"
                      step="0.01"
                      value={closeForm.close_price}
                      onChange={(e) => setCloseForm({ ...closeForm, close_price: parseFloat(e.target.value) || 0 })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fees</label>
                    <input
                      type="number"
                      step="0.01"
                      value={closeForm.close_fees}
                      onChange={(e) => setCloseForm({ ...closeForm, close_fees: parseFloat(e.target.value) || 0 })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2"
                    />
                  </div>
                </>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setCloseModalTrade(null)}
                  disabled={closeMutation.isPending}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  onClick={() => {
                    closeMutation.mutate({
                      id: closeModalTrade.id,
                      request: closeForm,
                    });
                  }}
                  disabled={closeMutation.isPending}
                  className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {closeMutation.isPending ? (
                    <>
                      <Spinner size="sm" />
                      Processing...
                    </>
                  ) : (
                    'Confirm'
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
