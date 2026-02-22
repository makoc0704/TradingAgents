import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout/Layout";
import DashboardPage from "./pages/DashboardPage";
import AnalysisPage from "./pages/AnalysisPage";
import AgentFlowPage from "./pages/AgentFlowPage";
import BacktestPage from "./pages/BacktestPage";
import PortfolioPage from "./pages/PortfolioPage";
import LiveTradingPage from "./pages/LiveTradingPage";
import RiskPage from "./pages/RiskPage";
import PipelinePage from "./pages/PipelinePage";
import HistoryPage from "./pages/HistoryPage";

export default function App() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route index element={<DashboardPage />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="agent-flow/:ticker/:date" element={<AgentFlowPage />} />
        <Route path="live" element={<LiveTradingPage />} />
        <Route path="backtest" element={<BacktestPage />} />
        <Route path="portfolio" element={<PortfolioPage />} />
        <Route path="risk" element={<RiskPage />} />
        <Route path="risk/:ticker/:date" element={<RiskPage />} />
        <Route path="pipeline" element={<PipelinePage />} />
        <Route path="history" element={<HistoryPage />} />
      </Route>
    </Routes>
  );
}
