import sys
from pathlib import Path
from datetime import datetime
import socket
import hashlib
import json
import requests
import subprocess
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

# === KONFIGURATION ===
SIGN_KEY_ID = None  # Optional: GPG-Key-ID, z. B. "max@example.org"
OUTPUT_DIR = Path(".")  # Zielordner, z. B. Path("/var/beweissicherung")

# === URL-ÜBERGABE ===
if len(sys.argv) != 2:
    print("❗ Verwendung: python webarchiv_beweis.py <URL>")
    sys.exit(1)

URL = sys.argv[1]

# === ZEITSTEMPEL UND ORDNERVERGABE ===
timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
parsed = urlparse(URL)
safe_host = parsed.netloc.replace(":", "_")
safe_path = parsed.path.strip("/").replace("/", "_") or "root"
base_name = f"{timestamp}_{safe_host}_{safe_path}"
folder = OUTPUT_DIR / base_name

counter = 1
while folder.exists():
    counter += 1
    folder = OUTPUT_DIR / f"{base_name}_v{counter}"
folder.mkdir(parents=True)

# === LOGSAMMLUNG ===
log_entries = []

def log(msg):
    entry = {"timestamp": datetime.utcnow().isoformat() + "Z", "message": msg}
    print(f"[{entry['timestamp']}] {msg}")
    log_entries.append(entry)

# === IP & HTML ABRUFEN ===
ip_address = socket.gethostbyname(parsed.netloc)
user_agent = "Mozilla/5.0 (Beweisarchivierung)"
response = requests.get(URL, headers={"User-Agent": user_agent})

(folder / "seite.html").write_text(response.text, encoding="utf-8")
(folder / "http_headers.json").write_text(json.dumps(dict(response.headers), indent=2), encoding="utf-8")
log("HTML-Inhalt und HTTP-Header gespeichert.")

# === METADATEN SPEICHERN ===
metadata = {
    "url": URL,
    "timestamp_utc": timestamp,
    "ip_address": ip_address,
    "http_status": response.status_code,
    "user_agent": user_agent,
}
(folder / "metadaten.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
log("Metadaten gespeichert.")

# === SCREENSHOT UND PDF ===
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle")
    page.screenshot(path=str(folder / "screenshot.png"), full_page=True)
    page.pdf(path=str(folder / "seite.pdf"), format="A4")
    browser.close()
log("Screenshot und PDF gespeichert.")

# === HASHWERTE ERZEUGEN ===
def sha256sum(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            h.update(chunk)
    return h.hexdigest()

hashfile = folder / "hashes.sha256"
with hashfile.open("w", encoding="utf-8") as f:
    for file in sorted(folder.glob("*.*")):
        if file.suffix == ".sig":
            continue
        checksum = sha256sum(file)
        f.write(f"{checksum}  {file.name}\n")
log("SHA256-Hashwerte gespeichert.")

# === GPG-SIGNATUR (OPTIONAL) ===
if SIGN_KEY_ID:
    sigfile = hashfile.with_suffix(".sig")
    subprocess.run([
        "gpg", "--default-key", SIGN_KEY_ID,
        "--output", str(sigfile),
        "--detach-sign", str(hashfile)
    ])
    log(f"GPG-Signatur erstellt: {sigfile.name}")

# === LOGDATEI ALS JSON SPEICHERN ===
logfile = folder / "verlauf.json"
logfile.write_text(json.dumps(log_entries, indent=2), encoding="utf-8")
log(f"Logdatei gespeichert: {logfile.name}")

# === ABSCHLUSS ===
log("✅ Webarchivierung abgeschlossen.")
log(f"Archivordner: {folder.resolve()}")
log(f"SHA256-Log: {hashfile.name}")
if SIGN_KEY_ID:
    log(f"Signiert mit: {SIGN_KEY_ID}")
