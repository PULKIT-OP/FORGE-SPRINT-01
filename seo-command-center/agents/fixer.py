import os
import json
import requests
from difflib import SequenceMatcher
from collections import defaultdict

# Configuration
MODEL = os.environ.get("RADAR_MODEL", "qwen3.5:9b")
OLLAMA_URL = "http://localhost:11434/api/generate"

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
        response = requests.post(OLLAMA_URL, json=payload, timeout=10)
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
                    f"Generate a high-converting SEO title for the page: {ctx['url']}\n"
                    f"Current H1: {ctx['h1']}\n"
                    f"Current Title: {old_title}\n"
                    f"Constraint: Maximum 60 characters. Return ONLY the title text."
                )
                new_title = call_model(prompt)
                if new_title and len(new_title) > 60:
                    new_title = call_model(f"Shorten this SEO title to under 60 chars: {new_title}. Return ONLY the text.")

                if new_title:
                    self.titles_fixes.append({"url": url, "old": old_title, "new": new_title})

            # 2. Meta Description Rewrite
            if url in (meta_issues.get("missing_meta_description", []) + meta_issues.get("meta_description_too_long", [])):
                old_meta = ctx["meta"]
                prompt = (
                    f"Generate a compelling SEO meta description for the page: {ctx['url']}\n"
                    f"H1: {ctx['h1']}\n"
                    f"Current Meta: {old_meta}\n"
                    f"Constraint: Maximum 155 characters. Return ONLY the description text."
                )
                new_meta = call_model(prompt)
                if new_meta and len(new_meta) > 155:
                    new_meta = call_model(f"Shorten this SEO meta description to under 155 chars: {new_meta}. Return ONLY the text.")

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
        self.rewrite_titles_and_metas()
        self.create_redirect_map()
        return {
            "titles": self.titles_fixes,
            "metas": self.metas_fixes,
            "redirect_map": self.redirect_map
        }
