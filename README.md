# 🕸️ Webarchiv-Beweissicherung (Python-Skript)

Dieses Skript dient der **gerichtsfesten Archivierung** und **technisch nachvollziehbaren Beweissicherung** von Webseiten zu einem bestimmten Zeitpunkt. Es speichert HTML-Inhalt, PDF und Screenshot einer URL, ergänzt um IP-Adresse, HTTP-Header und Metadaten, und versieht sämtliche Daten mit **SHA256-Hashwerten** zur Unveränderlichkeitsprüfung. Optional kann eine **digitale GPG-Signatur** erzeugt werden. Alle Aktionen werden in einer maschinenlesbaren **JSON-Protokolldatei** dokumentiert.

---

## ⚖️ Zweck

Mit diesem Tool können Webseiten zuverlässig dokumentiert werden, etwa zur:

- Beweissicherung in rechtlichen Verfahren
- Archivierung vergänglicher Online-Inhalte
- Nachweis von Online-Äußerungen, Veröffentlichungen
- Wahrung redaktioneller oder unternehmerischer Rechenschaftspflichten

---

## 🛠️ Funktionen

- Vollständiger Abruf einer Webseite (HTML, Screenshot, PDF)
- Speicherung technischer Metadaten (IP-Adresse, HTTP-Header, User-Agent)
- Erzeugung fester SHA256-Hashwerte für alle Inhalte
- Optional: digitale Signatur mittels GPG
- Automatische Versionierung bei Mehrfachaufrufen
- Protokollierung aller Schritte in einer `verlauf.json`-Datei
- Archivordner mit Zeitstempel und URL-Kennung

---

## 🚀 Installation

### Voraussetzungen

- [Python 3.10+](https://www.python.org/)
- [`uv`](https://github.com/astral-sh/uv) 
- [`playwright`](https://playwright.dev/python/) – für Screenshot & PDF (Chromium)

### Einrichtung

```bash
# Projektverzeichnis anlegen
mkdir webarchiv_beweis && cd webarchiv_beweis

# Virtuelle Umgebung erstellen
uv venv
source .venv/bin/activate  # Linux/macOS
.venv\Scripts\activate     # Windows

# Abhängigkeiten installieren
uv add requests playwright playwright install
```

---

## ▶️ Verwendung

### Grundbefehl

```bash
python webarchiv_beweis.py <URL>
```

Beispiel:

```bash
python webarchiv_beweis.py https://example.com/info/page
```

Die Daten werden im aktuellen Verzeichnis gespeichert. Du kannst das Zielverzeichnis im Skript mit `OUTPUT_DIR` anpassen.

### Optional: GPG-Signatur aktivieren

Im Skript `SIGN_KEY_ID` mit deiner GPG-Key-ID belegen:

```python
SIGN_KEY_ID = "max.mustermann@example.org"
```

GPG-Schlüssel generieren (falls noch nicht vorhanden):

```bash
gpg --full-generate-key
```

---

## 🗂️ Ergebnisstruktur

Das Skript erstellt einen chronologisch benannten Ordner z. B.:

```
20250412T154500Z_example.com_info_page/
├── seite.html            ← HTML-Quelltext
├── seite.pdf             ← Darstellung als PDF
├── screenshot.png        ← Vollbild-Screenshot
├── http_headers.json     ← HTTP-Header vom Server
├── metadaten.json        ← Zeit, IP, User-Agent, etc.
├── hashes.sha256         ← SHA256-Prüfsummen aller Dateien
├── verlauf.json          ← JSON-Protokoll aller Verarbeitungsschritte
└── hashes.sha256.sig     ← (optional) GPG-Signatur
```

Bei mehrmaligem Aufruf mit derselben URL und Zeitstempel wird automatisch `_v2`, `_v3`, ... angehängt.

---

## 🔐 Integritätsprüfung

Zur späteren Prüfung, ob Dateien unverändert sind:

```bash
sha256sum -c hashes.sha256
```

## 🧩 Erweiterungsideen

- Integration von Blockchain-Zeitstempeln
- ZIP-/WARC-Exportfunktion
- Web-Oberfläche zur Mehrfachverwendung

---

## 📄 Lizenz

Dieses Projekt steht unter der **MIT-Lizenz**. Verwendung auf eigene Verantwortung. Es wird keine Haftung für die juristische Verwertbarkeit oder Beweiskraft im Einzelfall übernommen.

