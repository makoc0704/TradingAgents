import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard", icon: "📊" },
  { to: "/analysis", label: "Analyse", icon: "🔍" },
  { to: "/backtest", label: "Backtest", icon: "📈" },
  { to: "/portfolio", label: "Portfolio", icon: "💼" },
  { to: "/pipeline", label: "Pipeline", icon: "⚙️" },
];

export default function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 z-30 flex h-screen w-56 flex-col border-r border-gray-800 bg-gray-950">
      <div className="flex h-16 items-center gap-2 border-b border-gray-800 px-5">
        <span className="text-xl">🤖</span>
        <span className="text-lg font-bold text-gray-100">TradingAgents</span>
      </div>

      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                isActive
                  ? "bg-blue-600/20 text-blue-400"
                  : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
              }`
            }
          >
            <span>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-gray-800 p-4 text-xs text-gray-600">
        TradingAgents v1.0
      </div>
    </aside>
  );
}
