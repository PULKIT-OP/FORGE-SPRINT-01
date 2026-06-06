import os
import json
import requests
from difflib import SequenceMatcher
from collections import defaultdict

# Configuration
MODEL = os.environ.get("RADAR_MODEL", "qwen3.5:9b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/generate")

def call_model(prompt):
    """Simple Ollama wrapper to generate text."""
    if getattr(call_model, "unavailable", False):
        return None

    try:
        payload = {
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3}
        }
        response = requests.post(OLLAMA_URL, json=payload, timeout=30)
        response.raise_for_status()
        # Reset failure count on success
        call_model.failures = 0
        return response.json().get("response", "").strip()
    except Exception as e:
        call_model.failures += 1
        print(f"[fixer] Model call failed ({call_model.failures}/3): {e}")
        if call_model.failures >= 3:
            print("[fixer] Too many failures. Marking model as unavailable for this run.")
            call_model.unavailable = True
        return None

def check_ai_availability():
    """Verify the Ollama server is reachable and the model is loaded."""
    print(f"[fixer] Checking AI availability (Model: {MODEL}, URL: {OLLAMA_URL})...")
    try:
        # Try a simple tags call to see if server is up
        tags_url = OLLAMA_URL.replace("/api/generate", "/api/tags")
        response = requests.get(tags_url, timeout=5)
        response.raise_for_status()
        tags_data = response.json()

        # Handle both possible Ollama response formats
        models_list = tags_data.get("models", [])
        if not models_list and "models" not in tags_data:
            # Some versions might have a different root key or just be a list
            models_list = tags_data if isinstance(tags_data, list) else []

        model_names = [m.get("name") if isinstance(m, dict) else str(m) for m in models_list]

        if any(MODEL in name for name in model_names):
            print(f"[fixer] AI is available and model {MODEL} is loaded.")
            return True

        # If tags are empty or model not found, try a tiny "ping" prompt as a fallback
        # because some local setups hide tags but allow generation.
        print(f"[fixer] Model {MODEL} not found in tags. Trying a ping request...")
        ping_payload = {"model": MODEL, "prompt": "hi", "stream": False}
        ping_resp = requests.post(OLLAMA_URL, json=ping_payload, timeout=5)
        if ping_resp.status_code == 200:
            print(f"[fixer] AI responded successfully to ping. Model {MODEL} is available.")
            return True
        else:
            print(f"[fixer] Ping failed with status {ping_resp.status_code}. Available models: {model_names}")
            return False
    except Exception as e:
        print(f"[fixer] AI server unreachable or error: {e}")
        return False

call_model.failures = 0
call_model.unavailable = False

class Fixer:
    def __init__(self, rows, issues):
        self.rows = {r["Address"]: r for r in rows}
        self.issues = issues
        self.titles_fixes = []
        self.metas_fixes = []
        self.redirect_map = []

    def _get_page_context(self, url):
        r = self.rows.get(url, {})
        return {
            "url": url,
            "h1": r.get("H1-1", ""),
            "title": r.get("Title 1", ""),
            "meta": r.get("Meta Description 1", ""),
            "content": r.get("Word Count", "0") # Just a proxy for content context
        }

    def rewrite_titles_and_metas(self):
        """Process pages with title and meta issues."""
        if getattr(call_model, "unavailable", False):
            return

        # Identify all affected URLs
        title_issues = {i["type"]: i["affected_urls"] for i in self.issues
                        if i["type"] in ("missing_title", "title_too_long")}
        meta_issues = {i["type"]: i["affected_urls"] for i in self.issues
                      if i["type"] in ("missing_meta_description", "meta_description_too_long")}

        all_affected = set(title_issues.get("missing_title", []) +
                           title_issues.get("title_too_long", []) +
                           meta_issues.get("missing_meta_description", []) +
                           meta_issues.get("meta_description_too_long", []))

        for url in all_affected:
            ctx = self._get_page_context(url)
            print(f"[fixer] Rewriting metadata for {url}...")

            # 1. Title Rewrite
            if url in (title_issues.get("missing_title", []) + title_issues.get("title_too_long", [])):
                old_title = ctx["title"]
                prompt = (
                    f"Task: Write a high-converting SEO page title.\n"
                    f"URL: {ctx['url']}\n"
                    f"Current H1: {ctx['h1']}\n"
                    f"Current Title: {old_title}\n"
                    f"Strict Constraint: The title MUST be between 30 and 60 characters. "
                    f"Return ONLY the title text, no quotes, no labels."
                )
                new_title = call_model(prompt)
                if new_title and (len(new_title) > 60 or len(new_title) < 30):
                    new_title = call_model(f"Adjust this title to be 30-60 characters: {new_title}. Return ONLY the text.")

                if new_title:
                    self.titles_fixes.append({"url": url, "old": old_title, "new": new_title})

            # 2. Meta Description Rewrite
            if url in (meta_issues.get("missing_meta_description", []) + meta_issues.get("meta_description_too_long", [])):
                old_meta = ctx["meta"]
                prompt = (
                    f"Task: Write a compelling SEO meta description.\n"
                    f"URL: {ctx['url']}\n"
                    f"H1: {ctx['h1']}\n"
                    f"Current Meta: {old_meta}\n"
                    f"Strict Constraint: The description MUST be between 120 and 155 characters. "
                    f"Return ONLY the description text, no quotes, no labels."
                )
                new_meta = call_model(prompt)
                if new_meta and (len(new_meta) > 155 or len(new_meta) < 120):
                    new_meta = call_model(f"Adjust this meta description to be 120-155 characters: {new_meta}. Return ONLY the text.")

                if new_meta:
                    self.metas_fixes.append({"url": url, "old": old_meta, "new": new_meta})

    def create_redirect_map(self):
        """Map 404s to the closest 200 indexable page."""
        broken_urls = []
        for i in self.issues:
            if i["type"] == "broken_link":
                broken_urls.extend(i["affected_urls"])

        # Collect all live, indexable pages for matching
        live_pages = [
            r["Address"] for r in self.rows.values()
            if (r.get("Status Code") == "200") and (r.get("Indexability", "").lower() == "indexable")
        ]

        if not live_pages:
            return

        for url in broken_urls:
            print(f"[fixer] Finding redirect target for {url}...")
            # Path similarity match
            best_match = None
            best_score = 0

            for live_url in live_pages:
                # Calculate similarity based on the path
                score = SequenceMatcher(None, url, live_url).ratio()
                if score > best_score:
                    best_score = score
                    best_match = live_url

            if best_match and best_score > 0.4: # Threshold to avoid random redirects
                self.redirect_map.append({
                    "from": url,
                    "to": best_match,
                    "reason": "Path similarity match" if best_score > 0.7 else "Section redirect"
                })

    def run(self):
        if not check_ai_availability():
            print("[fixer] Skipping AI-powered rewrites due to availability issues.")
            call_model.unavailable = True

        self.rewrite_titles_and_metas()
        self.create_redirect_map()
        return {
            "titles": self.titles_fixes,
            "metas": self.metas_fixes,
            "redirect_map": self.redirect_map
        }
