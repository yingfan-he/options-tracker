import { NavLink, Outlet } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Dashboard' },
  { to: '/trades', label: 'All Trades' },
  { to: '/add-trade', label: 'Add Trade' },
  { to: '/import', label: 'Import CSV' },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <h1 className="text-xl font-bold text-gray-900">Options Tracker</h1>
            <nav className="flex space-x-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      isActive
                        ? 'bg-blue-100 text-blue-700'
                        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
      <footer className="bg-white border-t border-gray-200 py-4">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center text-sm text-gray-500">
          Options Trading Tracker
        </div>
      </footer>
    </div>
  );
}
