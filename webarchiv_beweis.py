import sys
from pathlib import Path
from datetime import datetime, timezone
import socket
import hashlib
import json
import requests
import subprocess
import platform
import shutil
import whois
from urllib.parse import urlparse, urljoin
from playwright.sync_api import sync_playwright

# === KONFIGURATION ===
SIGN_KEY_ID = None
OUTPUT_DIR = Path(".")

# === URL-ÜBERGABE ===
if len(sys.argv) != 2:
    print("❗ Verwendung: python webarchiv_beweis.py <URL>")
    sys.exit(1)

URL = sys.argv[1]

# === ZEITSTEMPEL UND ORDNERVERGABE ===
timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
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
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "message": msg}
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

# === WHOIS-ABFRAGE ===
try:
    domain_whois = whois.whois(parsed.netloc)
    whois_path = folder / "whois.txt"
    whois_text = "\n".join(f"{k}: {v}" for k, v in domain_whois.items() if v)
    whois_path.write_text(whois_text, encoding="utf-8")
    log(f"WHOIS-Informationen gespeichert: {whois_path.name}")
except Exception as e:
    log(f"Fehler bei WHOIS-Abfrage: {e}")

# === DYNAMISCHE INHALTE & HAR & VIDEOS ===
with sync_playwright() as p:
    browser = p.chromium.launch()
    context = browser.new_context(record_har_path=str(folder / "network.har"))
    page = context.new_page()
    page.goto(URL, wait_until="networkidle")

    # Dynamisches HTML
    rendered_html = page.content()
    (folder / "seite_rendered.html").write_text(rendered_html, encoding="utf-8")
    log("Dynamisch gerenderter HTML-Inhalt gespeichert.")

    # Videos aus <video><source> und <video src=...>
    video_urls = set()
    video_urls.update(page.eval_on_selector_all("video source[src]", "els => els.map(el => el.src)"))
    video_urls.update(page.eval_on_selector_all("video[src]", "els => els.map(el => el.src)"))
    video_urls = {urljoin(URL, v) for v in video_urls if v}

    for i, video_url in enumerate(video_urls):
        try:
            vid_response = requests.get(video_url, stream=True, headers={"User-Agent": user_agent}, timeout=20)
            video_file = folder / f"video_{i+1}.mp4"
            with video_file.open("wb") as f:
                for chunk in vid_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            log(f"Video gespeichert: {video_file.name} von {video_url}")
        except Exception as e:
            log(f"Fehler beim Herunterladen von Video {i+1} ({video_url}): {e}")

    # Screenshot und PDF
    page.screenshot(path=str(folder / "screenshot.png"), full_page=True)
    page.pdf(path=str(folder / "seite.pdf"), format="A4")

    context.close()
    browser.close()
log("HAR, Screenshot, PDF und Videos gespeichert.")

# === HAR -> JSON extrahieren (optional) ===
try:
    har_path = folder / "network.har"
    har_json = json.loads(har_path.read_text(encoding="utf-8"))
    (folder / "network.json").write_text(json.dumps(har_json, indent=2), encoding="utf-8")
    log("HAR-Datei zusätzlich als JSON gespeichert.")
except Exception as e:
    log(f"Fehler beim Parsen der HAR-Datei: {e}")

# === TRACEROUTE (plattformabhängig via subprocess) ===
def save_traceroute_subprocess(domain: str, json_path: Path, txt_path: Path = None):
    log(f"Starte Traceroute (plattformabhängig) zu {domain} ...")
    system = platform.system()
    if system == "Windows":
        cmd = ["tracert", "-d", domain]
    else:
        traceroute_cmd = shutil.which("traceroute")
        if not traceroute_cmd:
            log("❌ traceroute-Befehl nicht gefunden.")
            return
        cmd = [traceroute_cmd, "-n", "-q", "1", "-w", "2", domain]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            log(f"Traceroute-Fehler: {result.stderr.strip()}")
            return

        lines = result.stdout.strip().splitlines()
        parsed = []
        for line in lines:
            line = line.strip()
            if not line or line.lower().startswith(("traceroute", "tracert")):
                continue
            parts = line.split()
            try:
                if system == "Windows":
                    ttl = int(parts[0])
                    ip = parts[-1]
                else:
                    ttl = int(parts[0])
                    ip = parts[1]
                parsed.append({"ttl": ttl, "ip": ip})
            except Exception:
                continue

        json_path.write_text(json.dumps(parsed, indent=2), encoding="utf-8")
        log("Traceroute (JSON) gespeichert.")
        if txt_path:
            txt_path.write_text("\n".join([f"{hop['ttl']}\t{hop['ip']}" for hop in parsed]), encoding="utf-8")
            log("Traceroute (TXT) gespeichert.")

    except Exception as e:
        log(f"Traceroute (subprocess) fehlgeschlagen: {e}")

save_traceroute_subprocess(
    parsed.netloc,
    folder / "traceroute.json",
    folder / "traceroute.txt"
)

# === HASHWERTE ===
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
