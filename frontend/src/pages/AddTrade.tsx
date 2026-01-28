import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createTrade, getOpenPositions } from '../api';
import type { TradeCreate } from '../types';
import Spinner from '../components/Spinner';

export default function AddTrade() {
  const queryClient = useQueryClient();
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [form, setForm] = useState<TradeCreate>({
    ticker: '',
    asset_type: 'Option',
    option_type: 'Call',
    action: 'STO',
    strike_price: 100,
    strike_price_2: null,
    expiration_date: getDefaultExpiration(),
    trade_date: new Date().toISOString().split('T')[0],
    quantity: 1,
    price_per_unit: 0,
    fees: 0,
    notes: '',
    linked_trade_id: null,
  });

  const { data: openPositions = [] } = useQuery({
    queryKey: ['openPositions'],
    queryFn: getOpenPositions,
  });

  const createMutation = useMutation({
    mutationFn: createTrade,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      queryClient.invalidateQueries({ queryKey: ['openPositions'] });
      queryClient.invalidateQueries({ queryKey: ['summary'] });
      setSuccessMessage(`Trade added successfully! (ID: ${data.id})`);
      setTimeout(() => setSuccessMessage(null), 3000);
      // Reset form
      setForm({
        ...form,
        ticker: '',
        price_per_unit: 0,
        fees: 0,
        notes: '',
        linked_trade_id: null,
      });
    },
  });

  function getDefaultExpiration(): string {
    const date = new Date();
    date.setDate(date.getDate() + 30);
    return date.toISOString().split('T')[0];
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.ticker.trim()) {
      alert('Please enter a ticker symbol');
      return;
    }
    createMutation.mutate({
      ...form,
      ticker: form.ticker.toUpperCase(),
    });
  };

  const updateForm = (updates: Partial<TradeCreate>) => {
    setForm({ ...form, ...updates });
  };

  // Get matching open positions for linking
  const matchingPositions = openPositions.filter(
    (p) => !form.ticker || p.ticker === form.ticker.toUpperCase()
  );

  // Determine available actions based on asset type
  const getActions = () => {
    switch (form.asset_type) {
      case 'Stock':
        return ['Buy', 'Sell'];
      case 'Spread':
        return ['BTO', 'STO', 'BTC', 'STC'];
      default:
        return ['STO', 'BTO', 'BTC', 'STC'];
    }
  };

  // Show link option for closing actions
  const showLinkOption = form.asset_type === 'Option' && ['BTC', 'STC'].includes(form.action);

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Add New Trade</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <div className="space-y-6">
              {/* Asset Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Asset Type</label>
                <div className="flex gap-2">
                  {(['Option', 'Stock', 'Spread'] as const).map((type) => (
                    <button
                      key={type}
                      type="button"
                      onClick={() => {
                        const newAction = type === 'Stock' ? 'Buy' : 'STO';
                        updateForm({
                          asset_type: type,
                          action: newAction,
                          option_type: type === 'Stock' ? null : 'Call',
                          strike_price: type === 'Stock' ? null : form.strike_price || 100,
                          strike_price_2: type === 'Spread' ? 110 : null,
                          expiration_date: type === 'Stock' ? null : form.expiration_date,
                        });
                      }}
                      className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                        form.asset_type === type
                          ? 'bg-blue-600 text-white'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      }`}
                    >
                      {type}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Left Column */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Ticker Symbol</label>
                    <input
                      type="text"
                      value={form.ticker}
                      onChange={(e) => updateForm({ ticker: e.target.value.toUpperCase() })}
                      placeholder="AAPL"
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  {form.asset_type !== 'Stock' && (
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Option Type</label>
                      <div className="flex gap-2">
                        {(['Call', 'Put'] as const).map((type) => (
                          <button
                            key={type}
                            type="button"
                            onClick={() => updateForm({ option_type: type })}
                            className={`flex-1 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                              form.option_type === type
                                ? type === 'Call' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                            }`}
                          >
                            {type === 'Call' ? '🟢' : '🔴'} {type}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Action</label>
                    <select
                      value={form.action}
                      onChange={(e) => updateForm({ action: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                    >
                      {getActions().map((action) => (
                        <option key={action} value={action}>{action}</option>
                      ))}
                    </select>
                  </div>

                  {form.asset_type !== 'Stock' && (
                    <>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Strike Price</label>
                        <input
                          type="number"
                          step="0.5"
                          value={form.strike_price || ''}
                          onChange={(e) => updateForm({ strike_price: parseFloat(e.target.value) || null })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                        />
                      </div>

                      {form.asset_type === 'Spread' && (
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Strike Price 2</label>
                          <input
                            type="number"
                            step="0.5"
                            value={form.strike_price_2 || ''}
                            onChange={(e) => updateForm({ strike_price_2: parseFloat(e.target.value) || null })}
                            className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                          />
                        </div>
                      )}

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Expiration Date</label>
                        <input
                          type="date"
                          value={form.expiration_date || ''}
                          onChange={(e) => updateForm({ expiration_date: e.target.value || null })}
                          className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </>
                  )}
                </div>

                {/* Right Column */}
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Trade Date</label>
                    <input
                      type="date"
                      value={form.trade_date}
                      onChange={(e) => updateForm({ trade_date: e.target.value })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Quantity ({form.asset_type === 'Stock' ? 'shares' : 'contracts'})
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={form.quantity}
                      onChange={(e) => updateForm({ quantity: parseInt(e.target.value) || 1 })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Price per {form.asset_type === 'Stock' ? 'share' : 'contract'}
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={form.price_per_unit}
                      onChange={(e) => updateForm({ price_per_unit: parseFloat(e.target.value) || 0 })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Fees</label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={form.fees}
                      onChange={(e) => updateForm({ fees: parseFloat(e.target.value) || 0 })}
                      className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                    />
                  </div>
                </div>
              </div>

              {/* Notes */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes</label>
                <textarea
                  value={form.notes || ''}
                  onChange={(e) => updateForm({ notes: e.target.value })}
                  placeholder="Optional notes..."
                  rows={3}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                />
              </div>

              {/* Link to Opening Trade */}
              {showLinkOption && matchingPositions.length > 0 && (
                <div className="border-t border-gray-200 pt-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Link to Opening Trade</label>
                  <select
                    value={form.linked_trade_id || ''}
                    onChange={(e) => updateForm({ linked_trade_id: e.target.value ? parseInt(e.target.value) : null })}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">None</option>
                    {matchingPositions.map((pos) => (
                      <option key={pos.id} value={pos.id}>
                        {pos.id}: {pos.ticker} {pos.option_type} ${pos.strike_price}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Success Message */}
              {successMessage && (
                <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded-lg flex items-center gap-2">
                  <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  {successMessage}
                </div>
              )}

              {/* Submit */}
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {createMutation.isPending ? (
                  <>
                    <Spinner size="sm" />
                    Adding Trade...
                  </>
                ) : (
                  'Add Trade'
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Quick Reference */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 h-fit">
          <h3 className="font-semibold text-gray-900 mb-4">Quick Reference</h3>

          <div className="space-y-4 text-sm">
            <div>
              <h4 className="font-medium text-gray-700 mb-2">Option Actions:</h4>
              <ul className="space-y-1 text-gray-600">
                <li><strong>STO</strong> - Sell to Open (CC/CSP)</li>
                <li><strong>BTO</strong> - Buy to Open (LEAP)</li>
                <li><strong>BTC</strong> - Buy to Close</li>
                <li><strong>STC</strong> - Sell to Close</li>
              </ul>
            </div>

            <div>
              <h4 className="font-medium text-gray-700 mb-2">Stock Actions:</h4>
              <ul className="space-y-1 text-gray-600">
                <li><strong>Buy</strong> / <strong>Sell</strong></li>
              </ul>
            </div>

            <div>
              <h4 className="font-medium text-gray-700 mb-2">Spreads:</h4>
              <ul className="space-y-1 text-gray-600">
                <li>Enter net debit/credit as price</li>
                <li>Use both strike fields</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
