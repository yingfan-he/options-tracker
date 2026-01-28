import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { previewCSV, importCSV } from '../api';
import type { CSVPreview, ImportResult } from '../types';

export default function ImportCSV() {
  const queryClient = useQueryClient();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CSVPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({
    ticker_col: '',
    action_col: '',
    strike_col: '',
    exp_date_col: '',
    trade_date_col: '',
    quantity_col: '',
    price_col: '',
    expired_col: '',
    notes_col: '',
  });
  const [result, setResult] = useState<ImportResult | null>(null);

  const previewMutation = useMutation({
    mutationFn: previewCSV,
    onSuccess: (data) => {
      setPreview(data);
      // Auto-detect column mappings
      const cols = data.columns;
      const findCol = (keywords: string[]) => {
        const found = cols.find((c) =>
          keywords.some((kw) => c.toLowerCase().includes(kw))
        );
        return found || '';
      };

      setMapping({
        ticker_col: findCol(['option', 'ticker', 'symbol']),
        action_col: findCol(['action']),
        strike_col: findCol(['strike']),
        exp_date_col: findCol(['expir', 'exp date']),
        trade_date_col: findCol(['transaction', 'trade date', 'date']),
        quantity_col: findCol(['contract', 'quantity', 'qty', '#']),
        price_col: findCol(['price', 'premium']),
        expired_col: findCol(['expired']),
        notes_col: findCol(['remark', 'note']),
      });
    },
  });

  const importMutation = useMutation({
    mutationFn: () => {
      if (!file) throw new Error('No file selected');
      return importCSV(file, mapping);
    },
    onSuccess: (data) => {
      setResult(data);
      queryClient.invalidateQueries({ queryKey: ['trades'] });
      queryClient.invalidateQueries({ queryKey: ['summary'] });
      queryClient.invalidateQueries({ queryKey: ['tickers'] });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setPreview(null);
      setResult(null);
      previewMutation.mutate(selectedFile);
    }
  };

  const handleImport = () => {
    const required = ['ticker_col', 'action_col', 'trade_date_col', 'quantity_col', 'price_col'];
    const missing = required.filter((key) => !mapping[key]);
    if (missing.length > 0) {
      alert('Please map required columns: Ticker, Action, Trade Date, Quantity, Price');
      return;
    }
    importMutation.mutate();
  };

  const columns = preview?.columns || [];

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Import Trades from CSV</h1>

      <div className="space-y-6">
        {/* File Upload */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <p className="text-gray-600 mb-4">
            Upload your CSV file. The importer handles messy data with various formats.
          </p>

          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>

        {/* Preview */}
        {preview && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Preview ({preview.row_count} rows)
            </h2>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-50">
                  <tr>
                    {columns.map((col) => (
                      <th key={col} className="px-3 py-2 text-left font-medium text-gray-600 whitespace-nowrap">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {preview.preview.slice(0, 5).map((row, i) => (
                    <tr key={i} className="border-t border-gray-100">
                      {columns.map((col) => (
                        <td key={col} className="px-3 py-2 whitespace-nowrap">
                          {String(row[col] ?? '')}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Column Mapping */}
        {preview && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Map Your Columns</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ticker column <span className="text-red-500">*</span>
                </label>
                <select
                  value={mapping.ticker_col}
                  onChange={(e) => setMapping({ ...mapping, ticker_col: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">-- Select --</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Action column <span className="text-red-500">*</span>
                </label>
                <select
                  value={mapping.action_col}
                  onChange={(e) => setMapping({ ...mapping, action_col: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">-- Select --</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Trade Date column <span className="text-red-500">*</span>
                </label>
                <select
                  value={mapping.trade_date_col}
                  onChange={(e) => setMapping({ ...mapping, trade_date_col: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">-- Select --</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Quantity column <span className="text-red-500">*</span>
                </label>
                <select
                  value={mapping.quantity_col}
                  onChange={(e) => setMapping({ ...mapping, quantity_col: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">-- Select --</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Price column <span className="text-red-500">*</span>
                </label>
                <select
                  value={mapping.price_col}
                  onChange={(e) => setMapping({ ...mapping, price_col: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">-- Select --</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Strike Price column</label>
                <select
                  value={mapping.strike_col}
                  onChange={(e) => setMapping({ ...mapping, strike_col: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">-- Skip --</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Expiration Date column</label>
                <select
                  value={mapping.exp_date_col}
                  onChange={(e) => setMapping({ ...mapping, exp_date_col: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">-- Skip --</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Expired? column</label>
                <select
                  value={mapping.expired_col}
                  onChange={(e) => setMapping({ ...mapping, expired_col: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">-- Skip --</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes column</label>
                <select
                  value={mapping.notes_col}
                  onChange={(e) => setMapping({ ...mapping, notes_col: e.target.value })}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2"
                >
                  <option value="">-- Skip --</option>
                  {columns.map((col) => (
                    <option key={col} value={col}>{col}</option>
                  ))}
                </select>
              </div>
            </div>

            <button
              onClick={handleImport}
              disabled={importMutation.isPending}
              className="mt-6 w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {importMutation.isPending ? 'Importing...' : 'Import Trades'}
            </button>
          </div>
        )}

        {/* Results */}
        {result && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Import Results</h2>

            {result.imported > 0 && (
              <div className="bg-green-50 text-green-800 px-4 py-3 rounded-lg mb-4">
                Successfully imported {result.imported} trades!
              </div>
            )}

            {result.total_errors > 0 && (
              <div className="space-y-2">
                <div className="bg-yellow-50 text-yellow-800 px-4 py-3 rounded-lg">
                  {result.total_errors} errors encountered
                </div>
                <details className="text-sm">
                  <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                    Show errors
                  </summary>
                  <ul className="mt-2 space-y-1 text-red-600">
                    {result.errors.map((err, i) => (
                      <li key={i}>{err}</li>
                    ))}
                  </ul>
                </details>
              </div>
            )}
          </div>
        )}

        {/* Error display */}
        {(previewMutation.isError || importMutation.isError) && (
          <div className="bg-red-50 text-red-800 px-4 py-3 rounded-lg">
            Error: {previewMutation.error?.message || importMutation.error?.message}
          </div>
        )}
      </div>
    </div>
  );
}
