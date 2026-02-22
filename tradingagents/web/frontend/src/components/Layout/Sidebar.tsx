import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Search,
  Activity,
  TrendingUp,
  Briefcase,
  Shield,
  Settings,
  Clock,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

const navItems = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/analysis", label: "Analyse", icon: Search },
  { to: "/live", label: "Live Trading", icon: Activity },
  { to: "/backtest", label: "Backtest", icon: TrendingUp },
  { to: "/portfolio", label: "Portfolio", icon: Briefcase },
  { to: "/risk", label: "Risk", icon: Shield },
  { to: "/pipeline", label: "Pipeline", icon: Settings },
  { to: "/history", label: "History", icon: Clock },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

export default function Sidebar({ collapsed, onToggle }: SidebarProps) {
  return (
    <aside
      className="fixed left-0 top-0 z-30 flex h-screen flex-col border-r transition-all duration-300"
      style={{
        width: collapsed ? "var(--sidebar-collapsed)" : "var(--sidebar-width)",
        background: "var(--bg-card)",
        borderColor: "var(--border)",
      }}
    >
      {/* Logo */}
      <div
        className="flex h-16 items-center gap-2.5 border-b px-4"
        style={{ borderColor: "var(--border)" }}
      >
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-blue-600/20">
          <Activity className="h-4.5 w-4.5 text-blue-400" />
        </div>
        {!collapsed && (
          <span className="text-base font-bold animate-fade-in" style={{ color: "var(--text-primary)" }}>
            TradingAgents
          </span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-0.5 px-2 py-3 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === "/"}
            title={collapsed ? item.label : undefined}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 ${
                isActive
                  ? "bg-blue-600/15 text-blue-400 shadow-sm shadow-blue-500/5"
                  : "hover:bg-[var(--bg-card-hover)]"
              }`
            }
            style={({ isActive }) => ({
              color: isActive ? undefined : "var(--text-secondary)",
            })}
          >
            <item.icon className="h-[18px] w-[18px] shrink-0" />
            {!collapsed && (
              <span className="animate-fade-in truncate">{item.label}</span>
            )}
          </NavLink>
        ))}
      </nav>

      {/* Collapse Toggle */}
      <div className="border-t p-2" style={{ borderColor: "var(--border)" }}>
        <button
          onClick={onToggle}
          className="flex w-full items-center justify-center rounded-lg px-3 py-2 transition-colors hover:bg-[var(--bg-card-hover)]"
          style={{ color: "var(--text-muted)" }}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" />
              <span className="ml-2 text-xs">Einklappen</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
