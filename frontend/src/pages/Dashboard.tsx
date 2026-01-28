import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { getSummary, getPremiumByPeriod, getOpenPositions, getStockPositions, loadSampleData, getTrades } from '../api';
import { useState } from 'react';
import Spinner from '../components/Spinner';

function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: '2-digit' });
}

function getDaysToExpiration(dateStr: string): number {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const expDate = new Date(dateStr);
  expDate.setHours(0, 0, 0, 0);
  return Math.ceil((expDate.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
}

export default function Dashboard() {
  const [period, setPeriod] = useState<'week' | 'month' | 'year'>('month');
  const queryClient = useQueryClient();

  const { data: trades } = useQuery({
    queryKey: ['trades'],
    queryFn: () => getTrades(),
  });

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['summary'],
    queryFn: getSummary,
    enabled: !!trades && trades.length > 0,
  });

  const { data: premiumData } = useQuery({
    queryKey: ['premium', period],
    queryFn: () => getPremiumByPeriod(period),
    enabled: !!trades && trades.length > 0,
  });

  const { data: openPositions } = useQuery({
    queryKey: ['openPositions'],
    queryFn: getOpenPositions,
  });

  const { data: stockPositions } = useQuery({
    queryKey: ['stockPositions'],
    queryFn: getStockPositions,
  });

  const sampleDataMutation = useMutation({
    mutationFn: loadSampleData,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      queryClient.invalidateQueries({ queryKey: ['summary'] });
      queryClient.invalidateQueries({ queryKey: ['openPositions'] });
      queryClient.invalidateQueries({ queryKey: ['stockPositions'] });
    },
  });

  // Show empty state if no trades
  if (!trades || trades.length === 0) {
    return (
      <div className="text-center py-12">
        <h2 className="text-2xl font-semibold text-gray-700 mb-4">No trades yet</h2>
        <p className="text-gray-500 mb-6">Add your first trade or load sample data to get started.</p>
        <button
          onClick={() => sampleDataMutation.mutate()}
          disabled={sampleDataMutation.isPending}
          className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed inline-flex items-center gap-2"
        >
          {sampleDataMutation.isPending ? (
            <>
              <Spinner size="sm" />
              Loading...
            </>
          ) : (
            'Load Sample Data'
          )}
        </button>
      </div>
    );
  }

  const chartData = premiumData?.slice(0, 12).reverse().map((item) => ({
    period: item.period,
    net: item.net_premium - item.total_fees,
  })) || [];

  return (
    <div className="space-y-6">
      {/* P&L Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Total P&L</p>
          <p className={`text-2xl font-bold mt-1 ${(summary?.total_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {summaryLoading ? '...' : formatCurrency(summary?.total_pnl || 0)}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Realized P&L</p>
          <p className={`text-2xl font-bold mt-1 ${(summary?.realized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {summaryLoading ? '...' : formatCurrency(summary?.realized_pnl || 0)}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Unrealized P&L</p>
          <p className={`text-2xl font-bold mt-1 ${(summary?.unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {summaryLoading ? '...' : formatCurrency(summary?.unrealized_pnl || 0)}
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <p className="text-sm font-medium text-gray-500">Total Fees</p>
          <p className="text-2xl font-bold mt-1 text-gray-700">
            {summaryLoading ? '...' : formatCurrency(summary?.total_fees || 0)}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Premium Chart */}
        <div className="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">Premium by Period</h2>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value as 'week' | 'month' | 'year')}
              className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="week">Week</option>
              <option value="month">Month</option>
              <option value="year">Year</option>
            </select>
          </div>
          {chartData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
                <Tooltip
                  formatter={(value) => [formatCurrency(value as number), 'Net Premium']}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb' }}
                />
                <Bar dataKey="net" radius={[4, 4, 0, 0]}>
                  {chartData.map((entry, index) => (
                    <Cell key={index} fill={entry.net >= 0 ? '#22c55e' : '#ef4444'} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-[300px] flex items-center justify-center text-gray-500">
              No premium data available
            </div>
          )}

          {/* Premium Table */}
          {premiumData && premiumData.length > 0 && (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-2 font-medium text-gray-600">Period</th>
                    <th className="text-right py-2 font-medium text-gray-600">Net Premium</th>
                    <th className="text-right py-2 font-medium text-gray-600">Fees</th>
                    <th className="text-right py-2 font-medium text-gray-600"># Trades</th>
                  </tr>
                </thead>
                <tbody>
                  {premiumData.slice(0, 12).map((row) => (
                    <tr key={row.period} className="border-b border-gray-100">
                      <td className="py-2">{row.period}</td>
                      <td className={`py-2 text-right ${row.net_premium >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {formatCurrency(row.net_premium)}
                      </td>
                      <td className="py-2 text-right text-gray-600">{formatCurrency(row.total_fees)}</td>
                      <td className="py-2 text-right text-gray-600">{row.num_trades}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Open Positions */}
        <div className="space-y-6">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Open Option Positions</h2>
            {!openPositions || openPositions.length === 0 ? (
              <p className="text-gray-500 text-sm">No open option positions</p>
            ) : (
              <div className="space-y-3">
                {openPositions.map((pos) => {
                  const daysToExp = getDaysToExpiration(pos.expiration_date);
                  const expColor = daysToExp < 0 ? 'text-red-600' : daysToExp <= 7 ? 'text-yellow-600' : 'text-green-600';
                  const typeIcon = pos.option_type === 'Call' ? '🟢' : '🔴';

                  return (
                    <div key={pos.id} className="border-b border-gray-100 pb-3 last:border-0">
                      <div className="font-medium">
                        {typeIcon} {pos.ticker} {pos.option_type} ${pos.strike_price}
                      </div>
                      <div className="text-sm text-gray-600">
                        {pos.action} {pos.quantity} @ ${pos.price_per_unit.toFixed(2)}
                      </div>
                      <div className={`text-sm ${expColor}`}>
                        Exp: {formatDate(pos.expiration_date)} ({daysToExp}d)
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Stock Positions</h2>
            {!stockPositions || stockPositions.length === 0 ? (
              <p className="text-gray-500 text-sm">No stock positions</p>
            ) : (
              <div className="space-y-2">
                {stockPositions.map((pos) => {
                  const avgCost = pos.shares > 0 ? pos.cost_basis / pos.shares : 0;
                  return (
                    <div key={pos.ticker} className="text-sm">
                      <span className="font-medium">{pos.ticker}</span>: {pos.shares} shares @ ${avgCost.toFixed(2)} avg
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
