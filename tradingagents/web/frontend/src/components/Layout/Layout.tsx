import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-gray-950">
      <Sidebar />
      <main className="ml-56 flex-1 p-8">
        <Outlet />
      </main>
    </div>
  );
}
