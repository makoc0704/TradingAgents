<p align="center">
  <img src="assets/TauricResearch.png" style="width: 60%; height: auto;">
</p>

<div align="center" style="line-height: 1;">
  <a href="https://arxiv.org/abs/2412.20138" target="_blank"><img alt="arXiv" src="https://img.shields.io/badge/arXiv-2412.20138-B31B1B?logo=arxiv"/></a>
  <a href="https://discord.com/invite/hk9PGKShPK" target="_blank"><img alt="Discord" src="https://img.shields.io/badge/Discord-TradingResearch-7289da?logo=discord&logoColor=white&color=7289da"/></a>
  <a href="./assets/wechat.png" target="_blank"><img alt="WeChat" src="https://img.shields.io/badge/WeChat-TauricResearch-brightgreen?logo=wechat&logoColor=white"/></a>
  <a href="https://x.com/TauricResearch" target="_blank"><img alt="X Follow" src="https://img.shields.io/badge/X-TauricResearch-white?logo=x&logoColor=white"/></a>
</div>

---

# TradingAgents: Multi-Agents LLM Financial Trading Framework

TradingAgents ist ein Multi-Agenten-Trading-Framework, das die Dynamik realer Handelsunternehmen nachbildet. Spezialisierte LLM-Agenten -- Fundamental-Analysten, Sentiment-Experten, technische Analysten, Researcher, Trader und ein Risikomanagement-Team -- bewerten gemeinsam Marktbedingungen und treffen Handelsentscheidungen durch strukturierte Debatten.

<p align="center">
  <img src="assets/schema.png" style="width: 100%; height: auto;">
</p>

> **Hinweis:** Dieses Framework dient Forschungszwecken. Trading-Performance haengt von vielen Faktoren ab (LLM-Modell, Datenqualitaet, Zeitraum). [Es stellt keine Finanz- oder Anlageberatung dar.](https://tauric.ai/disclaimer/)

---

## Inhaltsverzeichnis

- [Features](#features)
- [Architektur](#architektur)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Interfaces](#interfaces)
  - [Web-Interface](#web-interface)
  - [CLI](#cli)
  - [Python API](#python-api)
- [Web-Interface im Detail](#web-interface-im-detail)
  - [Dashboard](#dashboard)
  - [Analyse](#analyse)
  - [Agent Flow](#agent-flow)
  - [Backtest](#backtest)
  - [Portfolio](#portfolio)
  - [Live Trading](#live-trading)
  - [Risk Metrics](#risk-metrics)
  - [Pipeline](#pipeline)
  - [History](#history)
- [Live Trading Modul](#live-trading-modul)
- [Datenquellen](#datenquellen)
- [Projektstruktur](#projektstruktur)
- [Tests](#tests)
- [Contributing](#contributing)
- [Citation](#citation)

---

## Features

| Feature | Beschreibung |
|---------|-------------|
| **Multi-Agenten-Analyse** | 4 Analysten (Market, Fundamentals, News, Social), Bull/Bear-Researcher, Trader und Risikomanagement |
| **Strukturierte Debatten** | Agenten debattieren Investmentthesen und Risikoeinschaetzungen in mehreren Runden |
| **Web-Interface** | Modernes React-Dashboard mit Dark/Light Theme, Echtzeit-Fortschritt via WebSocket |
| **Backtesting** | Historische Simulation mit Equity-Kurven, Trade-Markern und Performance-Metriken |
| **Portfolio-Management** | Multi-Asset-Backtests mit Allokationsstrategien (Equal Weight, Risk Parity, Min Variance) |
| **Live Paper Trading** | Taegliches Trading mit Live-Daten ueber einen Dummy-Broker, persistenter Portfolio-State |
| **Automatisierte Pipeline** | Scheduling von Analyse-Jobs mit Cron-Ausdruecken und Benachrichtigungen |
| **Risikomanagement** | VaR, CVaR, Sharpe, Sortino, Drawdown, Beta, RSI und weitere Metriken |
| **Agent Memory** | ChromaDB-basiertes Erinnerungssystem fuer aehnliche Marktsituationen |
| **CLI** | Interaktive Terminal-Oberflaeche mit Rich-Formatierung |

---

## Architektur

```
                    ┌─────────────────────────────────────┐
                    │           Web-Interface              │
                    │  React 19 · Tailwind · Vite · WS    │
                    └──────────────┬──────────────────────┘
                                   │ REST + WebSocket
                    ┌──────────────▼──────────────────────┐
                    │         FastAPI Backend              │
                    │  Routers · TaskManager · LiveReader  │
                    └──────────────┬──────────────────────┘
                                   │
          ┌────────────────────────┼────────────────────────┐
          │                        │                        │
   ┌──────▼──────┐         ┌──────▼──────┐         ┌──────▼──────┐
   │  Backtesting │         │  Live Trading│         │  Pipeline   │
   │  Runner      │         │  Runner      │         │  Scheduler  │
   └──────┬──────┘         └──────┬──────┘         └──────┬──────┘
          │                        │                        │
          └────────────────────────┼────────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │      TradingAgentsGraph             │
                    │  LangGraph StateGraph Orchestrator   │
                    ├─────────────────────────────────────┤
                    │  Analysts → Researchers → Trader    │
                    │  → Risk Debate → Final Decision     │
                    └──────────────┬──────────────────────┘
                                   │
                    ┌──────────────▼──────────────────────┐
                    │          Dataflows                   │
                    │  yfinance · Alpha Vantage · OpenAI   │
                    └─────────────────────────────────────┘
```

### Agenten-Team

| Rolle | Agenten | Aufgabe |
|-------|---------|---------|
| **Analysten** | Market, Fundamentals, News, Social Media | Sammeln und bewerten Marktdaten aus verschiedenen Perspektiven |
| **Researcher** | Bull Researcher, Bear Researcher | Debattieren Investment-Thesen (bullish vs. bearish) |
| **Trader** | Trader Agent | Trifft die finale Handelsentscheidung auf Basis aller Reports |
| **Risiko** | Aggressive, Conservative, Neutral Debater | Bewerten Risiken und erstellen Risk-Assessment fuer den Portfolio Manager |

---

## Installation

### Voraussetzungen

- Python 3.10+
- Node.js 18+ (fuer das Web-Interface)

### Setup

```bash
git clone https://github.com/makoc0704/TradingAgents.git
cd TradingAgents

# Python Environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
# source .venv/bin/activate

# Abhaengigkeiten installieren
pip install -r requirements.txt
# oder mit uv:
uv sync
```

### API-Keys

Erstelle eine `.env`-Datei im Projektroot:

```env
OPENAI_API_KEY=sk-...
ALPHA_VANTAGE_API_KEY=...
```

OpenAI wird fuer alle LLM-Agenten benoetigt. [Alpha Vantage](https://www.alphavantage.co/support/#api-key) liefert Fundamental- und News-Daten (kostenloser Key verfuegbar).

---

## Konfiguration

Alle Einstellungen befinden sich in `tradingagents/default_config.py`:

```python
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()

# LLM-Modelle (guenstiger fuer Tests)
config["deep_think_llm"] = "o4-mini"
config["quick_think_llm"] = "gpt-4.1-mini"

# Debattierunden
config["max_debate_rounds"] = 1

# Datenquellen
config["data_vendors"] = {
    "core_stock_apis": "yfinance",
    "technical_indicators": "yfinance",
    "fundamental_data": "alpha_vantage",
    "news_data": "alpha_vantage",
}

# Backtesting-Profile: "quick", "standard", "full"
config["backtest_profile"] = "quick"
```

---

## Interfaces

TradingAgents bietet drei Interfaces: **Web-Interface**, **CLI** und **Python API**.

### Web-Interface

```bash
# Frontend bauen (einmalig)
cd tradingagents/web/frontend
npm install
npm run build
cd ../../..

# Server starten
python -m tradingagents.web
```

Das Web-Interface ist dann unter **http://localhost:8000** erreichbar.

Fuer die Entwicklung mit Hot-Reload:

```bash
# Terminal 1: Backend
python -m tradingagents.web --dev

# Terminal 2: Frontend Dev-Server
cd tradingagents/web/frontend
npm run dev
```

### CLI

```bash
python -m cli.main
```

Interaktive Oberflaeche mit Ticker-Auswahl, Datumsangabe, LLM-Konfiguration und Echtzeit-Fortschritt.

### Python API

```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

ta = TradingAgentsGraph(debug=True, config=DEFAULT_CONFIG.copy())
_, decision = ta.propagate("NVDA", "2024-05-10")
print(decision)
```

---

## Web-Interface im Detail

Das Web-Interface bietet eine Sidebar-Navigation mit Dark/Light Theme-Toggle. Alle langlebigen Operationen (Analyse, Backtest, Live-Run) laufen als Hintergrund-Tasks mit Echtzeit-Fortschritt ueber WebSocket.

### Dashboard

**Route:** `/`

Die Startseite zeigt eine Uebersicht:

- **Portfolio-Wert** mit SparkLine-Chart der Equity-Kurve
- **Gesamtrendite** und **Tagesrendite** des Live-Portfolios
- **Analysierte Ticker** mit Links zur Detail-Ansicht
- **Pipeline-Status** mit aktiven Jobs
- **Schnellaktionen** fuer direkten Zugriff auf Analyse, Backtest, Live Trading und Portfolio

### Analyse

**Route:** `/analysis`

Hier fuehrst du eine Einzelanalyse fuer einen Ticker durch:

1. **Ticker eingeben** (z.B. NVDA, AAPL)
2. **Datum waehlen** (das Analysedatum)
3. **Analysten auswaehlen** (Market, Social, News, Fundamentals)
4. **Analyse starten** -- der Fortschritt wird live per WebSocket angezeigt
5. **Ergebnis**: Signal (BUY/SELL/HOLD), Konfidenz-Score und Link zum Agent Flow

### Agent Flow

**Route:** `/agent-flow/:ticker/:date`

Visualisiert den kompletten Multi-Agenten-Entscheidungsprozess:

- **Flow-Diagramm**: Zeigt die Pipeline von Analysten ueber Debatten zur finalen Entscheidung
- **Analysten-Reports**: Aufklappbare Markdown-Berichte jedes Analysten (Market, Fundamentals, News, Sentiment)
- **Investment-Debatte**: Chat-artige Darstellung der Bull/Bear-Argumente
- **Risk-Debatte**: Aggressive vs. Conservative vs. Neutral Einschaetzungen
- **Finale Entscheidung**: Das Endergebnis mit Konfidenz-Meter

### Backtest

**Route:** `/backtest`

Simuliere die Agentenentscheidungen auf historischen Daten:

1. **Ticker, Start/Enddatum, Startkapital** konfigurieren
2. **Profil waehlen**: `quick` (schnell, weniger Runden), `standard`, `full` (komplett)
3. **Ergebnisse**:
   - KPI-Cards: Gesamtrendite, Sharpe Ratio, Max Drawdown, Endwert, Win Rate, Alpha
   - **Equity-Kurve** mit Trade-Markern (TradingView-Chart)
   - **Trade-Historie** mit Datum, Aktion, Preis, Stueckzahl

### Portfolio

**Route:** `/portfolio`

Multi-Asset Portfolio-Backtest:

1. **Ticker kommagetrennt eingeben** (z.B. NVDA, AAPL, MSFT)
2. **Allokationsstrategie waehlen**: Equal Weight, Risk Parity, Min Variance, Signal Weighted
3. **Ergebnisse**:
   - KPI-Cards: Gesamtrendite, Sharpe, Drawdown, Endwert
   - **Portfolio-Wert-Chart** (TradingView)
   - **Allokations-Tortendiagramm** mit Gewichtung pro Ticker
   - **Performance pro Ticker** als Tabelle

### Live Trading

**Route:** `/live`

Paper Trading mit Live-Marktdaten:

- **Portfolio-Uebersicht**: Aktueller Wert, Gesamtrendite, Tagesrendite, Cash-Bestand
- **Performance-KPIs**: Sharpe Ratio, Max Drawdown, Anzahl Trades, Win Rate
- **Equity-Kurve**: Historischer Portfolio-Verlauf als TradingView-Chart
- **Trade-Timeline**: Chronologische Darstellung aller Trades (BUY/SELL/HOLD)
- **Positionen**: Aktuelle Positionen mit Unrealized P&L
- **Jetzt traden**: Button fuer sofortigen Live-Run mit Fortschrittsanzeige

Der Live-Trading-State wird persistent in `live_portfolio/state.json` gespeichert und ueberlebt Server-Neustarts.

### Risk Metrics

**Route:** `/risk` oder `/risk/:ticker/:date`

Quantitative Risikoanalyse fuer einen Ticker:

- **KPI-Cards**: Annualisierte Volatilitaet, Max Drawdown, Sharpe Ratio, Sortino Ratio
- **Risk Radar**: Recharts RadarChart mit normalisierten Metriken (Volatilitaet, Drawdown, VaR, Beta, RSI, ATR)
- **Gauge Charts**: Visuelle Anzeigen fuer RSI, VaR 95%, Beta, Current Drawdown
- **Zusaetzliche Metriken**: Beta, VaR 99%, CVaR 95%, ATR, SMA 50/200, aktueller Kurs

### Pipeline

**Route:** `/pipeline`

Automatisierte Analyse-Jobs verwalten:

- **Status-Uebersicht**: Running/Stopped, Anzahl Jobs
- **Job-Tabelle**: Name, Typ, Cron-Ausdruck, naechste Ausfuehrung, letzter Status
- **Manuell ausloesen**: "Jetzt ausfuehren"-Button pro Job
- **Job-Historie**: Vergangene Ausfuehrungen mit Dauer und Ergebnis

Jobs werden in einer `pipeline.yaml` definiert und via APScheduler nach Cron-Zeitplan ausgefuehrt.

### History

**Route:** `/history`

Archiv aller bisherigen Analysen:

- **Suchfilter** fuer Ticker-Name
- **Tabelle**: Ticker, Datum, Signal, Konfidenz, Debatte vorhanden
- **Link zum Agent Flow** fuer jede Analyse

---

## Live Trading Modul

Das Live-Trading-Modul ermoeglicht taegliches Paper Trading mit realen Marktdaten:

```python
from tradingagents.live.runner import LiveRunner
from tradingagents.live.models import LiveConfig

config = LiveConfig(
    tickers=["NVDA", "AAPL"],
    initial_capital=200.0,
    mode="paper",
    broker_type="dummy",
    backtest_profile="quick",
)

runner = LiveRunner(config)
result = runner.run()
print(result.to_dict())
```

### Architektur

- **LiveRunner**: Orchestriert den Ablauf (Graph propagieren, Signale ausfuehren, State speichern)
- **DummyBroker**: Simuliert Orderausfuehrung mit konfigurierbarer Slippage und Kommission
- **LivePortfolioState**: Persistenter JSON-State (Cash, Positionen, Trade-History, Run-History)
- **LiveReader**: Read-Only-Service fuer das Web-Interface (Portfolio, Trades, Performance-Berechnung)

### Pipeline-Integration

Fuer taegliches automatisches Trading kann ein Pipeline-Job konfiguriert werden:

```yaml
# pipeline.yaml
jobs:
  - name: daily-live-trading
    type: live_trading
    cron: "0 16 * * 1-5"  # Mo-Fr um 16:00
    config:
      tickers: ["NVDA", "AAPL"]
      initial_capital: 200.0
```

---

## Datenquellen

| Quelle | Datentyp | Konfigurationskey |
|--------|----------|-------------------|
| **yfinance** | Aktienkurse, technische Indikatoren | `core_stock_apis`, `technical_indicators` |
| **Alpha Vantage** | Fundamentaldaten, News | `fundamental_data`, `news_data` |
| **OpenAI** | Fundamentals, News (alternativ) | `fundamental_data`, `news_data` |
| **Google News** | Nachrichten-Feed | `news_data` |
| **Reddit (PRAW)** | Social-Media-Sentiment | via Social Media Analyst |

Konfiguration in `DEFAULT_CONFIG["data_vendors"]`.

---

## Projektstruktur

```
TradingAgents/
├── tradingagents/
│   ├── agents/                 # LLM-Agenten
│   │   ├── analysts/           #   Market, Fundamentals, News, Social Media
│   │   ├── researchers/        #   Bull & Bear Researcher
│   │   ├── managers/           #   Research & Risk Manager
│   │   ├── risk_mgmt/          #   Aggressive, Conservative, Neutral Debater
│   │   ├── trader/             #   Trader Agent
│   │   └── utils/              #   Tools, Memory, States
│   ├── dataflows/              # Datenquellen-Abstraction
│   ├── graph/                  # LangGraph Workflow
│   ├── backtesting/            # Backtesting-Engine
│   ├── portfolio/              # Portfolio-Management & Optimierung
│   ├── live/                   # Live Paper Trading
│   │   ├── runner.py           #   LiveRunner Orchestrator
│   │   ├── broker/             #   BrokerInterface & DummyBroker
│   │   ├── state.py            #   Persistenter Portfolio-State
│   │   └── models.py           #   LiveConfig, LiveRunResult
│   ├── pipeline/               # Automatisierte Job-Pipeline
│   ├── risk/                   # Risikometriken-Berechnung
│   └── web/                    # Web-Interface
│       ├── app.py              #   FastAPI Application Factory
│       ├── routers/            #   API-Endpunkte (analysis, backtest, live, ...)
│       ├── services/           #   TaskManager, ResultReader, LiveReader
│       ├── schemas/            #   Pydantic Request/Response Models
│       └── frontend/           #   React 19 + TypeScript + Vite
│           └── src/
│               ├── pages/      #     9 Pages (Dashboard, Analysis, ...)
│               ├── components/ #     Layout, Charts, Common Components
│               ├── hooks/      #     useWebSocket, useApi, useInterval
│               ├── api/        #     Typisierter API Client
│               └── types/      #     TypeScript Interfaces
├── cli/                        # CLI-Interface (Typer + Rich)
├── tests/                      # pytest Test Suite
├── .cursor/rules/              # Cursor-AI Konventionen
├── setup.py                    # Package-Definition
├── pyproject.toml              # Moderne Python-Konfiguration
└── requirements.txt            # Python-Abhaengigkeiten
```

---

## Tests

```bash
# Alle Tests
uv run python -m pytest tests/ -v

# Live Trading Tests
uv run python -m pytest tests/test_live/ -v

# Web-Interface Tests
uv run python -m pytest tests/test_web/ -v

# Einzelne Test-Dateien
uv run python -m pytest tests/test_web/test_live_reader.py -v
uv run python -m pytest tests/test_web/test_live_router.py -v
```

Alle API-Calls und LLM-Aufrufe werden in den Tests gemockt.

---

## Contributing

Wir freuen uns ueber Beitraege! Ob Bugfixes, Dokumentation oder neue Features -- jeder Input hilft. Fuer Beitraege bitte die Konventionen in `.cursor/rules/git-conventions.mdc` beachten.

**Commit-Format:** `type(scope): beschreibung` (z.B. `feat(web): add risk metrics page`)

## Citation

```bibtex
@misc{xiao2025tradingagentsmultiagentsllmfinancial,
      title={TradingAgents: Multi-Agents LLM Financial Trading Framework},
      author={Yijia Xiao and Edward Sun and Di Luo and Wei Wang},
      year={2025},
      eprint={2412.20138},
      archivePrefix={arXiv},
      primaryClass={q-fin.TR},
      url={https://arxiv.org/abs/2412.20138},
}
```
