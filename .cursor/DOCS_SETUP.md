# Cursor Docs Setup

Diese Docs sollten in Cursor eingebunden werden, damit der Agent bei der Entwicklung
auf die korrekte API-Dokumentation zugreifen kann.

## Einrichtung

1. Öffne **Cursor Settings** (Ctrl+Shift+J oder Zahnrad unten links)
2. Gehe zu **Features** → **Docs**
3. Klicke auf **"+ Add new doc"**
4. Füge folgende Docs hinzu:

## Empfohlene Docs

| Name | URL | Priorität | Verwendung |
|------|-----|-----------|------------|
| LangGraph | https://langchain-ai.github.io/langgraph/ | Hoch | Graph-Architektur, StateGraph, Nodes, Edges |
| LangChain | https://python.langchain.com/docs/ | Hoch | ChatOpenAI, Prompts, Tools, Memory |
| backtrader | https://www.backtrader.com/docu/ | Hoch | Backtesting-Integration (Phase 2) |
| yfinance | https://ranaroussi.github.io/yfinance/ | Mittel | Aktiendaten, Fundamentals |
| Alpha Vantage | https://www.alphavantage.co/documentation/ | Mittel | API-Referenz für Fundamentals, News |
| ChromaDB | https://docs.trychroma.com/ | Mittel | Vektor-Datenbank für Agenten-Memory |
| Rich | https://rich.readthedocs.io/en/stable/ | Niedrig | CLI-UI-Erweiterung |
| FastAPI | https://fastapi.tiangolo.com/ | Niedrig | Web-Interface (Phase 5) |
| CCXT | https://docs.ccxt.com/ | Niedrig | Broker-Anbindung (Phase 6) |
| pytest | https://docs.pytest.org/en/stable/ | Niedrig | Testing-Framework |

## Nutzung in Prompts

Nach dem Einrichten können Docs in Prompts mit `@Docs` referenziert werden:
- "@LangGraph wie erstelle ich einen conditional edge?"
- "@backtrader wie implementiere ich eine custom Strategy?"
