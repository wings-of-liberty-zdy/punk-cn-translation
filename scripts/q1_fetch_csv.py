import sys; sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import json, os, socket

URL = ("https://docs.google.com/spreadsheets/d/e/"
       "2PACX-1vTF4s2BdJrSSrwYgrHgye7QDmyF4y73XqnxG1nCCuxnGiHK_Zxo4Q1EFsrvoDoWaEMNsqgRmzK0gaqm"
       "/pub?gid=0&single=true&output=csv")
OUT = r"C:\Users\houdezaiwu\Documents\github\punk-cn-translation\data\dump"

print("=== DNS resolution ===")
for host in ("docs.google.com",):
    try:
        infos = socket.getaddrinfo(host, 443)
        ips = sorted({i[4][0] for i in infos})
        print(f"  {host} -> {ips}")
    except Exception as e:
        print(f"  {host} FAILED {e!r}")

print("\n=== requests GET ===")
try:
    import requests
    r = requests.get(URL, timeout=30, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    print("status", r.status_code, "len", len(r.content), "ctype", r.headers.get("Content-Type"))
    print("final url", r.url)
    if r.status_code == 200 and r.content:
        open(os.path.join(OUT, "q1_remote_shop.csv"), "wb").write(r.content)
        txt = r.content.decode("utf-8", errors="replace")
        lines = txt.splitlines()
        print("csv lines:", len(lines))
        print("--- first 8 lines ---")
        for ln in lines[:8]:
            print("   ", ln[:400])
    else:
        print("body head:", r.text[:500])
except Exception as e:
    print("requests FAILED:", repr(e))
    try:
        import urllib.request
        req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        print("urllib ok len", len(data))
        open(os.path.join(OUT, "q1_remote_shop.csv"), "wb").write(data)
        for ln in data.decode("utf-8", errors="replace").splitlines()[:8]:
            print("   ", ln[:400])
    except Exception as e2:
        print("urllib FAILED:", repr(e2))
