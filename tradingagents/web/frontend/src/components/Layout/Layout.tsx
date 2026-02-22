import { useState } from "react";
import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import ThemeToggle from "./ThemeToggle";

export default function Layout() {
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem("sidebar-collapsed") === "true");

  function handleToggle() {
    setCollapsed((prev) => {
      const next = !prev;
      localStorage.setItem("sidebar-collapsed", String(next));
      return next;
    });
  }

  return (
    <div className="flex min-h-screen" style={{ background: "var(--bg-primary)" }}>
      <Sidebar collapsed={collapsed} onToggle={handleToggle} />
      <div
        className="flex flex-1 flex-col transition-all duration-300"
        style={{
          marginLeft: collapsed ? "var(--sidebar-collapsed)" : "var(--sidebar-width)",
        }}
      >
        <header
          className="sticky top-0 z-20 flex h-14 items-center justify-end border-b px-6 glass"
          style={{ borderColor: "var(--border)" }}
        >
          <ThemeToggle />
        </header>
        <main className="flex-1 p-6 lg:p-8 animate-fade-in">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
