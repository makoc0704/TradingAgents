import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import DashboardPage from "./pages/DashboardPage";
import AnalysisPage from "./pages/AnalysisPage";
import BacktestPage from "./pages/BacktestPage";
import PortfolioPage from "./pages/PortfolioPage";
import PipelinePage from "./pages/PipelinePage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="backtest" element={<BacktestPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="pipeline" element={<PipelinePage />} />
      </Route>
    </Routes>
  );
}
