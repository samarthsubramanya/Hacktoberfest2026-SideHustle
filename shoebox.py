"""Shoebox: a local-only receipt sorter for gig workers and freelancers.

Drop receipt photos in a folder, run `python shoebox.py ./receipts`, review in the browser,
export a Schedule C summary. Every pixel stays on this machine: the model runs in Ollama.
"""
import argparse, base64, csv, hashlib, io, json, os, sys, urllib.error, urllib.request
from collections import defaultdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OLLAMA = "http://" + os.environ.get("OLLAMA_HOST", "localhost:11434") + "/api/chat"
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

# Schedule C (Form 1040) Part II expense lines. Value = share that's deductible.
CATEGORIES = {
    "8 Advertising": 1, "9 Car and truck expenses": 1, "10 Commissions and fees": 1,
    "11 Contract labor": 1, "15 Insurance": 1, "17 Legal and professional services": 1,
    "18 Office expense": 1, "20a Rent/lease: vehicles & equipment": 1,
    "20b Rent/lease: other business property": 1, "21 Repairs and maintenance": 1,
    "22 Supplies": 1, "23 Taxes and licenses": 1, "24a Travel": 1,
    "24b Meals (50%)": 0.5, "25 Utilities": 1, "27a Other expenses": 1,
    "Personal (not deductible)": 0,
}

SCHEMA = {
    "type": "object",
    "properties": {
        "vendor": {"type": "string"},
        "date": {"type": "string", "description": "YYYY-MM-DD"},
        "total": {"type": "number"},
        "tax": {"type": "number"},
        "payment": {"type": "string"},
        "items": {"type": "string", "description": "short summary of what was bought"},
        # reason before category: the model writes its argument first, then commits to a line
        "reason": {"type": "string"},
        "category": {"type": "string", "enum": list(CATEGORIES)},
    },
    "required": ["vendor", "date", "total", "tax", "payment", "items", "reason", "category"],
}

PROMPT = """You are a bookkeeper for a self-employed {work}.
Read this receipt and return JSON. Use the grand total actually paid (after tips/discounts).
Use 0 for tax if none is shown. Date as YYYY-MM-DD.
Pick the IRS Schedule C line that best fits for a {work}; if it is clearly a personal purchase,
use "Personal (not deductible)". Give a one-sentence reason a tax preparer would accept.

Guide:
- 9 Car and truck expenses: gas, fuel, car wash, parking, tolls, oil change for a work vehicle
- 10 Commissions and fees: platform/marketplace fees taken from your earnings (Uber service fee, Etsy fees)
- 18 Office expense: software subscriptions, postage, small office items
- 22 Supplies: ink, paper, materials consumed in the work
- 24b Meals (50%): food or coffee with a client or while traveling for work
- 25 Utilities: phone and internet bills
- Personal (not deductible): groceries, household items, personal food"""


def load_image(path):
    """Phone photos are huge; shrink to 1280px so the local model stays fast."""
    try:
        from PIL import Image
        im = Image.open(path).convert("RGB")
        im.thumbnail((1280, 1280))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=90)
        return buf.getvalue()
    except ImportError:  # ponytail: no Pillow means full-size images, just slower
        return path.read_bytes()


def extract(path, model, work):
    body = {
        "model": model, "stream": False, "think": False, "format": SCHEMA,
        "options": {"temperature": 0, "num_predict": 3000},  # room for qwen3-vl to think, but a runaway model still stops
        "messages": [{"role": "user", "content": PROMPT.format(work=work),
                      "images": [base64.b64encode(load_image(path)).decode()]}],
    }
    req = urllib.request.Request(OLLAMA, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            msg = json.loads(r.read())["message"]
        # qwen3-vl ignores think:false on newer Ollama; on older ones the JSON lands in "thinking"
        data = json.loads(msg.get("content") or msg.get("thinking") or "{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(json.loads(e.read()).get("error", e)) from None
    if data.get("category") not in CATEGORIES:
        data["category"] = "27a Other expenses"
    return data


def scan(folder, model, work):
    db_path = folder / "shoebox.json"
    db = json.loads(db_path.read_text()) if db_path.exists() else {}
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTS)
    for i, p in enumerate(files, 1):
        rid = hashlib.sha1(p.read_bytes()).hexdigest()[:12]  # same photo twice = one receipt
        if rid in db:
            continue
        print(f"[{i}/{len(files)}] reading {p.name} ...", end=" ", flush=True)
        try:
            rec = extract(p, model, work)
        except Exception as e:  # one bad photo shouldn't sink the batch
            print(f"failed: {e}")
            continue
        db[rid] = {"file": p.name, "reviewed": False, **rec}
        db_path.write_text(json.dumps(db, indent=2))  # save after each so a crash loses nothing
        print(f"{rec['vendor']} ${rec['total']:.2f} -> {rec['category']}")
    return db


def summary(db):
    lines = defaultdict(float)
    for r in db.values():
        lines[r["category"]] += float(r["total"]) * CATEGORIES[r["category"]]
    return {k: round(lines[k], 2) for k in CATEGORIES if k in lines and CATEGORIES[k]}  # form order


def to_csv(db):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["date", "vendor", "items", "total", "tax", "payment", "schedule_c_line", "deductible", "reason", "file"])
    for r in sorted(db.values(), key=lambda r: r["date"]):
        w.writerow([r["date"], r["vendor"], r["items"], r["total"], r["tax"], r["payment"], r["category"],
                    round(float(r["total"]) * CATEGORIES[r["category"]], 2), r["reason"], r["file"]])
    w.writerow([])
    w.writerow(["SCHEDULE C SUMMARY"])
    for k, v in summary(db).items():
        w.writerow([k, v])
    return out.getvalue()


def serve(folder, port):
    db_path = folder / "shoebox.json"
    page = Path(__file__).parent / "review.html"

    class H(BaseHTTPRequestHandler):
        def send(self, body, ctype="application/json", extra=()):
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            for k, v in extra:
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            db = json.loads(db_path.read_text())
            if self.path == "/":
                self.send(page.read_bytes(), "text/html")
            elif self.path == "/api":
                self.send(json.dumps({"receipts": db, "categories": CATEGORIES, "summary": summary(db)}).encode())
            elif self.path == "/export.csv":
                self.send(to_csv(db).encode(), "text/csv",
                          [("Content-Disposition", "attachment; filename=shoebox.csv")])
            elif self.path.startswith("/img/"):
                name = Path(self.path[5:]).name  # strip any ../ tricks
                rec = next((r for r in db.values() if r["file"] == name), None)
                if not rec:
                    return self.send_error(404)
                self.send((folder / name).read_bytes(), "image/" + (Path(name).suffix[1:].lower().replace("jpg", "jpeg")))
            else:
                self.send_error(404)

        def do_POST(self):  # POST /api/<id> with fields to update
            rid = self.path.rsplit("/", 1)[-1]
            db = json.loads(db_path.read_text())
            if rid not in db:
                return self.send_error(404)
            patch = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if "category" in patch and patch["category"] not in CATEGORIES:
                return self.send_error(400)
            allowed = {"vendor", "date", "total", "tax", "category", "reviewed"}
            db[rid].update({k: v for k, v in patch.items() if k in allowed})
            db_path.write_text(json.dumps(db, indent=2))
            self.send(json.dumps({"summary": summary(db)}).encode())

        def log_message(self, *a):
            pass

    print(f"Review at http://localhost:{port}  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()  # localhost only, never the LAN


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("folder", type=Path)
    ap.add_argument("--work", default="freelancer", help='what you do, e.g. "rideshare driver"')
    ap.add_argument("--model", default="qwen3-vl:8b")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-serve", action="store_true")
    a = ap.parse_args()
    if not a.folder.is_dir():
        sys.exit(f"{a.folder} is not a folder")
    db = scan(a.folder, a.model, a.work)
    print(f"\n{len(db)} receipts. Deductible by Schedule C line:")
    for k, v in summary(db).items():
        print(f"  {k:<42} ${v:>9,.2f}")
    if not a.no_serve:
        serve(a.folder, a.port)


if __name__ == "__main__":
    main()
