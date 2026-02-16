Phase 2: Weiterentwicklung – Empfohlene Reihenfolge
Die Reihenfolge basiert auf Abhängigkeiten – jeder Schritt baut auf dem vorherigen auf:
┌──────────────────────────────────────────────────┐│ 1. Risikoquantifizierung                         ││    (Grundlage für Backtesting & Portfolio)        │├──────────────────────────────────────────────────┤│ 2. Backtesting-Framework                         ││    (braucht quantitative Metriken)               │├──────────────────────────────────────────────────┤│ 3. Portfolio-Management                          ││    (braucht Backtesting zur Validierung)         │├──────────────────────────────────────────────────┤│ 4. Automatisierte Pipeline / Scheduler           ││    (braucht Portfolio-Management)                │├──────────────────────────────────────────────────┤│ 5. Web-Interface                                 ││    (visualisiert alles oben)                     │├──────────────────────────────────────────────────┤│ 6. Broker-Anbindung                              ││    (letzter Schritt – echtes Geld, höchstes      ││     Risiko, braucht alles andere)                │└──────────────────────────────────────────────────┘
Phase 3: Cursor-Workflow für jedes Feature
Für jedes der 6 Features empfehle ich diesen Ablauf:
Schritt 1: Ask Mode – Architektur planen
> "Analysiere die bestehende Architektur und entwirf ein Konzept für [Feature X]. Welche bestehenden Dateien müssen angepasst werden? Welche neuen Module brauchen wir?"
Schritt 2: Rule erstellen
Bevor du codest, eine Rule für das neue Modul anlegen, z.B.:
> "Erstelle eine Cursor Rule für das Backtesting-Modul mit den Konventionen, die wir gerade besprochen haben."
Schritt 3: Agent Mode – Implementierung
Arbeite Feature für Feature ab. Gib klare, abgegrenzte Aufgaben:
> "Implementiere die BacktestEngine-Klasse in tradingagents/backtesting/engine.py basierend auf unserem Architektur-Konzept."
Nicht: "Bau das ganze Backtesting-Framework."
Schritt 4: Agent Mode – Tests
> "Schreibe pytest-Tests für das Backtesting-Modul. Mocke alle API-Calls."
Schritt 5: Ask Mode – Review
> "Review den neuen Backtesting-Code. Gibt es Inkonsistenzen mit dem Rest des Projekts? Fehlen Edge Cases?