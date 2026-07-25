#!/usr/bin/env python3
"""Download all Google Docs as DOCX, extract text to markdown vault."""

import json, os, sys, zipfile, xml.etree.ElementTree as ET, re, time
from pathlib import Path
import urllib.request, urllib.error

CRED_FILE = Path("/root/forex-grid/google-cred.json")
TOKEN_FILE = Path("/root/forex-grid/google-token.json")
DOCX_DIR = Path("/root/forex-grid/google-docs-docx")
VAULT_DIR = Path("/root/Obsidian Vault/Google Docs")

DOCX_DIR.mkdir(parents=True, exist_ok=True)
VAULT_DIR.mkdir(parents=True, exist_ok=True)

with open(TOKEN_FILE) as f:
    token_data = json.load(f)
TOKEN = token_data.get("access_token") or token_data.get("id_token")
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def list_docs():
    import urllib.request
    url = "https://www.googleapis.com/drive/v3/files?q=mimeType='application/vnd.google-apps.document'&pageSize=100&fields=files(id,name)"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data.get("files", [])

def download_docx(file_id, name):
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}/export?mimeType=application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    safe = re.sub(r'[^\w\s-]', '', name).strip().replace(' ', '_')[:80]
    if not safe: safe = file_id
    docx_path = DOCX_DIR / f"{safe}.docx"
    if docx_path.exists():
        print(f"  [{safe}.docx] already exists, skipping download")
        return docx_path
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req) as resp:
            data = resp.read()
        docx_path.write_bytes(data)
        print(f"  [{safe}.docx] OK ({len(data)//1024}KB)")
        return docx_path
    except urllib.error.HTTPError as e:
        print(f"  [{safe}.docx] FAILED HTTP {e.code}")
        return None

def docx_to_markdown(docx_path):
    """Extract text from DOCX using stdlib (no python-docx needed)."""
    try:
        with zipfile.ZipFile(docx_path) as z:
            xml_bytes = z.read("word/document.xml")
    except Exception as e:
        return f"*Error: could not read DOCX* — {e}"
    root = ET.fromstring(xml_bytes)
    ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    texts = []
    for t in root.iter("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"):
        if t.text:
            texts.append(t.text)
    return "\n".join(texts)

def extract_to_vault(docx_path, doc_name, doc_id):
    text = docx_to_markdown(docx_path)
    safe_filename = re.sub(r'[^\w\s-]', '', doc_name).strip().replace(' ', '_')[:80]
    if not safe_filename: safe_filename = doc_id
    md_path = VAULT_DIR / f"{safe_filename}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {doc_name}\n\n")
        f.write(f"> **Source**: Google Docs — `{doc_id}`\n")
        f.write(f"> **Downloaded**: {time.strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write("---\n\n")
        f.write(text)
    print(f"  → {md_path.name} ({len(text)} chars)")

def main():
    print("STEP 1/3: Listing Google Docs...")
    docs = list_docs()
    print(f"  Found {len(docs)} docs\n")

    print("STEP 2/3: Downloading all as DOCX...")
    downloaded = []
    for d in docs:
        p = download_docx(d["id"], d["name"])
        if p: downloaded.append((p, d["name"], d["id"]))

    print(f"\nSTEP 3/3: Extracting text to vault ({len(downloaded)} docs)...")
    for docx_path, name, fid in downloaded:
        extract_to_vault(docx_path, name, fid)

    print(f"\nDone! {len(downloaded)} docs processed → {VAULT_DIR}")
    print(f"DOCX files at {DOCX_DIR}")

if __name__ == "__main__":
    main()
