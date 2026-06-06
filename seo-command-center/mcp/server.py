"""
server.py — local MCP server + live dashboard host (one process, two faces).

  1. MCP tools over stdio  -> Claude Code calls: seo_load, seo_detect, seo_report, seo_export
  2. HTTP + SSE on localhost:7700 -> the live cockpit that fills as issues are found.

STARTER: works end to end out of the box. Extend the detectors (seo/detector.py) and
the fixes (the model-driven title rewriting / redirect map) during the Sprint.

Needs the MCP SDK to expose tools to Claude (`pip install mcp`); without it the dashboard
still runs so you can use run.py. Standard library otherwise.
"""
from __future__ import annotations
import json, os, queue, threading, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DASH_DIR = os.path.join(ROOT, "dashboard")
OUT_DIR = os.path.join(ROOT, "outputs")
PORT = int(os.environ.get("SEO_PORT", "7700"))
MODEL = os.environ.get("RADAR_MODEL", "qwen3.5:9b")

import sys
sys.path.insert(0, ROOT)
from seo import detector  # noqa: E402

RUN = {"site": None, "urls": 0, "issues": [], "summary": None, "status": "idle"}
_subs: list[queue.Queue] = []
_lock = threading.Lock()


def _emit(event, data):
    payload = json.dumps({"event": event, "data": data})
    with _lock:
        for q in list(_subs):
            try: q.put_nowait(payload)
            except Exception: pass


# ----- pipeline tools (importable by run.py without MCP) -----
def seo_load(export_dir: str) -> dict:
    rows = detector.load_rows(export_dir)
    RUN.update({"rows": rows, "urls": len(rows), "issues": [], "summary": None,
                "site": _guess_site(rows), "status": "running"})
    _emit("loaded", {"site": RUN["site"], "urls": len(rows)})
    return {"urls": len(rows), "site": RUN["site"]}


def _guess_site(rows):
    if not rows: return "unknown"
    addr = rows[0].get("Address", "")
    try:
        from urllib.parse import urlparse
        return urlparse(addr).netloc or "unknown"
    except Exception:
        return "unknown"


def seo_detect() -> dict:
    issues = detector.detect(RUN.get("rows", []))
    RUN["issues"] = issues
    RUN["summary"] = detector.summarize(issues)
    for i in issues:
        _emit("issue", i)
    _emit("summary", RUN["summary"])
    return {"detected": len(issues), "summary": RUN["summary"]}


def _report_obj() -> dict:
    return {
        "site": RUN["site"],
        "urls_crawled": RUN["urls"],
        "summary": RUN["summary"] or {"total_issues": 0, "by_severity": {}},
        "issues": RUN["issues"],
        "fixes": RUN.get("fixes", {"titles": [], "redirect_map": [], "metas": []}),
        "recommendations": RUN.get("recommendations", []),
        "run_meta": {"model": MODEL, "model_calls": RUN.get("model_calls", 0),
                     "duration_sec": RUN.get("duration_sec", 0)},
    }


def seo_set_fixes(titles=None, redirect_map=None, metas=None) -> dict:
    RUN["fixes"] = {"titles": titles or [], "redirect_map": redirect_map or [], "metas": metas or []}
    _emit("fixes", RUN["fixes"]); return {"titles": len(titles or []), "redirects": len(redirect_map or []), "metas": len(metas or [])}


def seo_recommend(recommendations: list) -> dict:
    RUN["recommendations"] = recommendations
    _emit("recommendations", {"recommendations": recommendations}); return {"count": len(recommendations)}


def seo_report() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, "report.json")
    json.dump(_report_obj(), open(p, "w", encoding="utf-8"), indent=2)
    RUN["status"] = "done"; _emit("saved", {"path": p}); return {"path": p}


def seo_export() -> dict:
    os.makedirs(OUT_DIR, exist_ok=True)
    p = os.path.join(OUT_DIR, "report.html")
    open(p, "w", encoding="utf-8").write(_render_html(_report_obj()))
    _emit("exported", {"path": p}); return {"path": p}


def _render_html(o) -> str:
    sev = (o["summary"] or {}).get("by_severity", {})
    total_issues = (o["summary"] or {}).get("total_issues", 0)

    # Calculate a simple Health Score (A-F)
    grade_map = {0: "A", 1: "A-", 2: "B+", 3: "B", 4: "B-", 5: "C+", 6: "C", 7: "C-", 8: "D+", 9: "D", 10: "D-", 11: "F"}
    score_idx = min(total_issues, 11)
    grade = grade_map.get(score_idx, "F")

    rows = "".join(
        f'<tr><td><span class="sev {i["severity"].lower()}">{i["severity"]}</span></td>'
        f'<td>{i["type"].replace("_", " ").title()}</td><td>{i["count"]}</td>'
        f'<td>{i.get("explanation") or ""}</td></tr>'
        for i in sorted(o["issues"], key=lambda x: {"High":0,"Medium":1,"Low":2}.get(x["severity"],3)))

    recs = "".join(f"<li>{r}</li>" for r in o.get("recommendations", []))

    # Showcase some fixes
    fix_samples = ""
    titles = o.get("fixes", {}).get("titles", [])
    metas = o.get("fixes", {}).get("metas", [])

    if titles or metas:
        fix_samples = '<div class="card"><h3 style="margin-top:0">Automatic Fixes Preview</h3>'
        all_samples = []
        for t in titles[:3]:
            all_samples.append(f"<div><b>Title:</b><br><span class='before'>{t['old']}</span><br>&rarr;<br><span class='after'>{t['new']}</span></div>")
        for m in metas[:3]:
            all_samples.append(f"<div><b>Meta:</b><br><span class='before'>{m['old']}</span><br>&rarr;<br><span class='after'>{m['new']}</span></div>")
        fix_samples += '<div class="fix-grid">' + "".join(f'<div class="fix-item">{s}</div>' for s in all_samples) + '</div></div>'

    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>SEO Audit Report — {o['site']}</title>
<style>
body{{font-family:'Inter', 'Segoe UI', Roboto, sans-serif;background:#f4f7f9;color:#2d3436;margin:0;padding:40px;line-height:1.6}}
.wrap{{max-width:900px;margin:0 auto}}
header{{display:flex;justify-content:space-between;align-items:flex-end;margin-bottom:32px;border-bottom:3px solid #0984e3;padding-bottom:20px}}
h1{{font-size:32px;margin:0;color:#2d3436}}
.sub{{color:#636e72;font-size:16px}}
.card{{background:#fff;border:1px solid #dfe6e9;border-radius:12px;padding:24px;margin-bottom:24px;box-shadow:0 4px 6px rgba(0,0,0,0.05)}}
.grade-card{{text-align:center;background:linear-gradient(135deg, #0984e3, #6c5ce7);color:#fff;border:none}}
.grade-big{{font-size:72px;font-weight:800;display:block;line-height:1}}
.grade-label{{font-size:18px;text-transform:uppercase;letter-spacing:1px;opacity:0.9}}
.k{{display:flex;gap:32px;flex-wrap:wrap;align-items:center}}
.k div{{font-size:14px;color:#636e72}}
.k b{{display:block;font-size:32px;color:#2d3436}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:10px}}
th,td{{text-align:left;padding:12px 15px;border-bottom:1px solid #dfe6e9}}
th{{font-size:12px;text-transform:uppercase;color:#b2bec3;letter-spacing:0.5px}}
.sev{{font-size:11px;font-weight:700;padding:4px 10px;border-radius:6px;text-transform:uppercase}}
.sev.high{{background:#ffeaa7;color:#d63031;border:1px solid #fab1a0}}
.sev.medium{{background:#e1f5fe;color:#0288d1;border:1px solid #b3e5fc}}
.sev.low{{background:#f1f2f6;color:#636e72;border:1px solid #dfe6e9}}
.fix-grid{{display:grid;grid-template-columns:repeat(auto-fit, minmax(250px, 1fr));gap:20px;margin-top:15px}}
.fix-item{{background:#f9f9f9;padding:15px;border-radius:8px;font-size:13px;border-left:4px solid #0984e3}}
.before{{color:#b2bec3;text-decoration:line-through;font-size:12px}}
.after{{color:#2d3436;font-weight:600}}
ul{{padding-left:20px}}li{{margin:10px 0;color:#2d3436}}
.muted{{color:#b2bec3;font-size:13px;text-align:center;margin-top:40px}}
</style></head><body><div class="wrap">
<header><div><h1>SEO Audit Report</h1><div class="sub">{o['site']} · {o['urls_crawled']} URLs crawled</div></header>
<div class="card grade-card">
    <span class="grade-label">Overall Health Grade</span>
    <span class="grade-big">{grade}</span>
    <div class="k" style="justify-content:center;color:#fff;margin-top:20px">
        <div style="color:#fff"><b style="color:#fff">{total_issues}</b>total issues</div>
        <div style="color:#fff"><b style="color:#fff">{sev.get('High',0)}</b>high</div>
        <div style="color:#fff"><b style="color:#fff">{sev.get('Medium',0)}</b>medium</div>
        <div style="color:#fff"><b style="color:#fff">{sev.get('Low',0)}</b>low</div>
    </div>
</div>
<div class="card"><h3>Prioritized Issue List</h3><table><thead><tr><th>Severity</th><th>Issue Type</th><th>Impact (URLs)</th><th>Description</th></tr></thead>
<tbody>{rows or '<tr><td colspan=4 class="muted">No issues detected.</td></tr>'}</tbody></table></div>
{fix_samples}
<div class="card"><h3>Strategic Recommendations</h3><ul>{recs or '<li class="muted">No specific recommendations generated.</li>'}</ul></div>
<p class="muted">Generated by SEO Command Center · Model: {o.get('run_meta',{}).get('model','')} · {o.get('run_meta',{}).get('duration_sec','')}s</p></div></body></html>"""


# ----- dashboard HTTP host -----
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="text/html; charset=utf-8"):
        self.send_response(code); self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-cache"); self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            p = os.path.join(DASH_DIR, "index.html")
            self._send(200, open(p, encoding="utf-8").read() if os.path.exists(p) else "no dashboard")
        elif self.path == "/app.js":
            p = os.path.join(DASH_DIR, "app.js")
            self._send(200, open(p, encoding="utf-8").read() if os.path.exists(p) else "", "application/javascript")
        elif self.path == "/state":
            self._send(200, json.dumps({k: v for k, v in RUN.items() if k != "rows"}), "application/json")
        elif self.path == "/events":
            self.send_response(200); self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache"); self.end_headers()
            q = queue.Queue()
            with _lock: _subs.append(q)
            try:
                snap = {k: v for k, v in RUN.items() if k != "rows"}
                self.wfile.write(f"data: {json.dumps({'event':'snapshot','data':snap})}\n\n".encode()); self.wfile.flush()
                while True:
                    try: self.wfile.write(f"data: {q.get(timeout=15)}\n\n".encode())
                    except queue.Empty: self.wfile.write(b": ping\n\n")
                    self.wfile.flush()
            except Exception: pass
            finally:
                with _lock:
                    if q in _subs: _subs.remove(q)
        else: self._send(404, "not found")


def start_dashboard(port=PORT):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def _run_mcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except Exception:
        print(f"[seo] MCP SDK not found. Dashboard only at http://localhost:{PORT}", flush=True)
        while True: time.sleep(3600)
    mcp = FastMCP("seo-command-center")

    @mcp.tool()
    def load(export_dir: str) -> dict:
        """Load a Screaming Frog export directory (expects internal_all.csv)."""
        return seo_load(export_dir)

    @mcp.tool()
    def detect_issues() -> dict:
        """Run the SEO rulebook detectors over the loaded crawl."""
        return seo_detect()

    @mcp.tool()
    def set_fixes(titles: list = None, redirect_map: list = None, metas: list = None) -> dict:
        """Attach the model-written title rewrites and the redirect map."""
        return seo_set_fixes(titles, redirect_map, metas)

    @mcp.tool()
    def recommend(recommendations: list) -> dict:
        """Attach the prioritized recommendations."""
        return seo_recommend(recommendations)

    @mcp.tool()
    def write_report() -> dict:
        """Write outputs/report.json."""
        return seo_report()

    @mcp.tool()
    def export_report() -> dict:
        """Write outputs/report.html (the client deliverable)."""
        return seo_export()

    mcp.run()


if __name__ == "__main__":
    start_dashboard()
    print(f"[seo] dashboard live at http://localhost:{PORT}", flush=True)
    _run_mcp()
