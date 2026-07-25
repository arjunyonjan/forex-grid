#!/usr/bin/env python3
"""Google Docs → DOCX downloader. Lists docs, downloads as .docx to Download folder."""

import json, os, socket, threading, urllib.parse, sys, time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

DIR = Path("/storage/emulated/0/Obsidian Vault/credentials")
DIR.mkdir(exist_ok=True)
TOKEN_FILE = DIR / "token.json"
CRED_FILE = DIR / "client_secret.json"
DL_DIR = Path("/storage/emulated/0/Download")
DL_DIR.mkdir(exist_ok=True)

SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/documents.readonly",
]

if not CRED_FILE.exists():
    print("No client_secret.json in credentials/")
    sys.exit(1)

with open(CRED_FILE) as f:
    creds_data = json.load(f)
CLIENT_ID = creds_data["installed"]["client_id"]
CLIENT_SECRET = creds_data["installed"]["client_secret"]
REDIRECT_URI = "http://localhost:8080"

class Handler(BaseHTTPRequestHandler):
    auth_code = None
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        if "code" in params:
            Handler.auth_code = params["code"][0]
            self.wfile.write(b"<h1>Auth OK! Close this tab.</h1>")
        else:
            self.wfile.write(b"<h1>Auth failed.</h1>")
        threading.Thread(target=self.server.shutdown).start()
    def log_message(self, *args):
        pass

def get_token():
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE) as f:
            token = json.load(f)
        if "access_token" in token:
            if token.get("expires_at", 0) > time.time() + 60:
                return token["access_token"]
            if "refresh_token" in token:
                print("Refreshing token...")
                r = requests.post("https://oauth2.googleapis.com/token", data={
                    "refresh_token": token["refresh_token"],
                    "client_id": CLIENT_ID,
                    "client_secret": CLIENT_SECRET,
                    "grant_type": "refresh_token",
                })
                if r.status_code == 200:
                    new = r.json()
                    token["access_token"] = new["access_token"]
                    token["expires_at"] = time.time() + new.get("expires_in", 3600)
                    with open(TOKEN_FILE, "w") as f:
                        json.dump(token, f, indent=2)
                    return token["access_token"]
    return None

def do_auth():
    token = get_token()
    if token:
        return token
    auth_url = (
        f"https://accounts.google.com/o/oauth2/auth?"
        f"client_id={CLIENT_ID}&redirect_uri={urllib.parse.quote(REDIRECT_URI)}&"
        f"scope={urllib.parse.quote(' '.join(SCOPES))}&"
        f"response_type=code&access_type=offline&prompt=select_account+consent"
    )
    print("\nOpening Chrome for Google auth...")
    os.system(f"termux-open-url '{auth_url}'")
    print(f"\nIf Chrome doesn't open, visit:\n{auth_url}\n")
    server = HTTPServer(("localhost", 8080), Handler)
    print("Waiting for auth callback on http://localhost:8080 ...")
    server.serve_forever()
    if not Handler.auth_code:
        print("No auth code received.")
        sys.exit(1)
    print("Exchanging code for token...")
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "code": Handler.auth_code,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    })
    if r.status_code != 200:
        print(f"Token exchange failed: {r.text}")
        sys.exit(1)
    token_data = r.json()
    token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)
    print("Token saved.")
    return token_data["access_token"]

def list_docs(token):
    headers = {"Authorization": f"Bearer {token}"}
    q = "mimeType='application/vnd.google-apps.document'"
    r = requests.get(
        "https://www.googleapis.com/drive/v3/files",
        params={"q": q, "pageSize": 100, "fields": "files(id,name,createdTime,modifiedTime,size)"},
        headers=headers,
    )
    if r.status_code != 200:
        print(f"Drive API error: {r.text}")
        return []
    return r.json().get("files", [])

def download_docx(token, file_id, name):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export"
    params = {"mimeType": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    print(f"  Downloading: {name} ...", end=" ", flush=True)
    r = requests.get(url, params=params, headers=headers, stream=True)
    if r.status_code != 200:
        print(f"FAILED ({r.status_code})")
        return None
    safe_name = "".join(c for c in name if c.isalnum() or c in " _-.").strip()
    if not safe_name:
        safe_name = file_id
    if not safe_name.endswith(".docx"):
        safe_name += ".docx"
    path = DL_DIR / safe_name
    with open(path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)
    sz = path.stat().st_size
    print(f"OK ({sz//1024}KB)")
    return path

def main():
    action = sys.argv[1] if len(sys.argv) > 1 else "list"

    print("STEP 1/3: Authenticating...")
    token = do_auth()

    if action == "list":
        print("STEP 2/3: Listing Google Docs...")
        docs = list_docs(token)
        if not docs:
            print("  No Google Docs found.")
        else:
            print(f"  Found {len(docs)} docs:\n")
            for d in docs:
                mod = d.get("modifiedTime", "")[:10]
                print(f"  [{d['id']}] {d['name']}  (modified {mod})")
        print(f"\nTo download: python3 {sys.argv[0]} download <file-id>")
        print(f"To download all: python3 {sys.argv[0]} download-all")

    elif action == "download" and len(sys.argv) >= 3:
        file_id = sys.argv[2]
        name = sys.argv[3] if len(sys.argv) >= 4 else file_id
        print("STEP 2/3: Downloading doc...")
        path = download_docx(token, file_id, name)
        if path:
            print(f"\n  Saved to: {path}")

    elif action == "download-all":
        docs = list_docs(token)
        if not docs:
            print("  No Google Docs found.")
            return
        print(f"STEP 2/3: Downloading all {len(docs)} docs...")
        ok = 0
        for d in docs:
            p = download_docx(token, d["id"], d["name"])
            if p:
                ok += 1
        print(f"\nDownloaded {ok}/{len(docs)} docs to {DL_DIR}")

    else:
        print("Usage:")
        print(f"  python3 {sys.argv[0]} list              — list all Google Docs")
        print(f"  python3 {sys.argv[0]} download <id>     — download one doc as DOCX")
        print(f"  python3 {sys.argv[0]} download-all       — download ALL docs as DOCX")
        print(f"  python3 {sys.argv[0]} download-id <url>  — download from Google Docs URL")
        sys.exit(1)

if __name__ == "__main__":
    main()
