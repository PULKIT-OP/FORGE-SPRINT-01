# PROMPTS.md — my key prompts log

Keep the handful of prompts that actually moved the build. Not every message — the ones that
mattered: the system/sub-agent prompts, the ones you iterated on, the "this finally worked"
moment. This shows how you direct an AI, which is graded (challenge brief section 08).

Format per entry:
- **Prompt** (paste it)
- **For:** what you were trying to do
- **Revised?** did you have to change it, and why

---

## Example (replace with your own)

- **Prompt:** "Extend seo/detector.py to detect redirect chains: build a map of {Address ->
  Redirect URL} for all 3xx rows, then a chain exists when a Redirect URL is itself a key in
  that map. Add a redirect_chain issue (High). Run python seo/detector.py and show counts."
- **For:** adding the redirect-chain detector
- **Revised?** Yes — first version flagged single redirects as chains; added the "target is
  also a redirecting URL" condition.

---

## My prompts

1. **Prompt:** "Extend seo/detector.py to complete the rulebook (rulebook.md).

Add these 10 missing detectors to the detect() function (after the existing orphan_page check):

1. title_too_short (Low): Title 1 Length < 30 AND Title 1 is not empty, on indexable 200 pages
2. missing_meta_description (Medium): Meta Description 1 empty on indexable 200 pages
3. duplicate_meta_description (Medium): Same non-empty Meta Description 1 on 2+ indexable 200 pages
4. meta_description_too_long (Low): Meta Description 1 Length > 155 on indexable 200 pages
5. missing_h1 (Medium): H1-1 empty on 200 pages (any indexability)
6. duplicate_h1 (Low): Same non-empty H1-1 on 2+ indexable 200 pages
7. redirect_chain (High): Build {Address → Redirect URL} map for all 3xx rows. A chain exists when a Redirect URL is a key in that map. Flag the 3xx URL as affected.
8. thin_content (Low): Word Count < 200 on indexable 200 pages
9. non_indexable_but_linked (Medium): Indexability = "Non-Indexable" AND Inlinks > 0 (any status code)
10. slow_page (Low): Response Time > 1.0 (all rows)

**Key rules:**
- Duplicate checks: only compare indexable 200 pages
- Title/meta/H1 checks: only on text/html + indexable 200 pages (use idx200 list)
- H1 check: on 200 pages, not just indexable
- Use _int() and _float() helpers for parsing
- For redirect_chain, check if a 3xx URL's Redirect URL appears as a key (Address) in the 3xx map

**Output format:** Each add() call: type, severity, list of affected URLs, explanation string.

**Test:** Run `python run.py sample-export/` — the issue count should increase from current baseline."

- **For:** completing the detector.py for remaining parts.
- **Revised?** For now NO, it is working fine.
