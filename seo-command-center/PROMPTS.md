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

1. - **Prompt:** "Extend seo/detector.py to complete the rulebook (rulebook.md).

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

2. - **Prompt:** "Build the fixer agent to rewrite issues and create a redirect map. This is the champion-tier 
value-add that turns detection into actionable fixes.

FILE: Create or update seo-command-center/agents/fixer.py (new file)

REQUIREMENTS:

1. **Title & Meta Rewriter** (for pages flagged: missing_title, title_too_long, 
   missing_meta_description, meta_description_too_long)
   - For each affected URL from the issues list, get the page row from internal_all.csv
   - Use the model to generate an optimized title (≤ 60 chars / ≤ 561 px) using:
     - Page URL
     - Existing H1-1 (if present)
     - Existing copy / content context
   - Use the model to generate a meta description (≤ 155 chars)
   - **VALIDATE in code**: If title > 60 chars or meta > 155 chars, ask model once more to shorten
   - Collect {url, old_title, new_title, old_meta, new_meta} for each

2. **Redirect Map** (for broken_link pages)
   - For each 404 page, find the closest live (status 200, indexable) URL
   - Match by path similarity (e.g., /blog/old-post → /blog/new-post)
   - Produce {from: 404_url, to: live_url, reason: "Path match" or "Section redirect"}

3. **Integration**
   - Call MCP set_fixes(titles, redirects) to store results
   - Keep each model call to ONE page (small context)
   - Log which pages were fixed

INPUT: issues list from seo_detect() in mcp/server.py
OUTPUT: Store in mcp/server.py RUN["fixes"] dict with structure matching report.schema.json

CONSTRAINTS:
- Model calls must be small (one page per call)
- Validate title/meta lengths before storing
- Never hard-code URLs
- Test with: python run.py sample-export/"
- **For:** to make the fixer agent to rewrite the issue found
- **Revised?** this particular prompt made the agent and report-schema.json updated server.py and other files but when i tested it, it was looping continusly because it was not getting ollama model which it needs to work as per the model it made so i recitfied the issue with claude and updated prompt is right below.

3. - **Prompt:** "when i am running this command python ./seo-command-center/run.py sample-export/ i am getting this 
  error : PS C:\Users\PULKIT\Desktop\FORGE_01> python ./seo-command-center/run.py sample-export/     
  [seo] dashboard: http://localhost:7700                                                             
                                                                                                     
  [seo] Generating actionable fixes...                                                               
  [fixer] Rewriting metadata for https://nmgtechnologies.com/industry/healthcare...                  
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Rewriting metadata for https://nmgtechnologies.com/services/it-consulting/...              
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Rewriting metadata for                                                                     
  https://nmgtechnologies.com/services/custom-software-development/php-development/...               
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Rewriting metadata for                                                                     
  https://nmgtechnologies.com/success-stories/international-insurance...                             
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Rewriting metadata for https://nmgtechnologies.com/industry/staffing...                    
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Rewriting metadata for https://nmgtechnologies.com/privacy-policy...                       
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Rewriting metadata for https://nmgtechnologies.com/blog/ui-ux-mobile-app-development...    
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Rewriting metadata for                                                                     
  https://nmgtechnologies.com/ai-enhanced-web-mobile-application-development...                      
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Model call failed: 404 Client Error: Not Found for url:                                    
  http://localhost:11434/api/generate                                                                
  [fixer] Rewriting metadata for https://nmgtechnologies.com/ai-driven-business-tra                  
  ──── (92 lines hidden) ─────────────────────────────────────────────────────────────────────────── 
  rn session.request(method=method, url=url, **kwargs)                                               
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                                       
    File                                                                                             
  "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\sessions.py",  
  line 589, in request                                                                               
      resp = self.send(prep, **send_kwargs)                                                          
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                                                          
    File                                                                                             
  "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\sessions.py",  
  line 703, in send                                                                                  
      r = adapter.send(request, **kwargs)                                                            
          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                                                            
    File                                                                                             
  "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\site-packages\requests\adapters.py",  
  line 486, in send                                                                                  
      resp = conn.urlopen(                                                                           
             ^^^^^^^^^^^^^                                                                           
    File "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connecti 
  onpool.py", line 793, in urlopen                                                                   
      response = self._make_request(                                                                 
                 ^^^^^^^^^^^^^^^^^^^                                                                 
    File "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connecti 
  onpool.py", line 496, in _make_request                                                             
      conn.request(                                                                                  
    File                                                                                             
  "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connection.py", 
  line 400, in request                                                                               
      self.endheaders()                                                                              
    File "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 1322, in 
  endheaders                                                                                         
      self._send_output(message_body, encode_chunked=encode_chunked)                                 
    File "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 1081, in 
  _send_output                                                                                       
      self.send(msg)                                                                                 
    File "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\http\client.py", line 1025, in 
  send                                                                                               
      self.connect()                                                                                 
    File                                                                                             
  "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connection.py", 
  line 238, in connect                                                                               
      self.sock = self._new_conn()                                                                   
                  ^^^^^^^^^^^^^^^^                                                                   
    File                                                                                             
  "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\connection.py", 
  line 198, in _new_conn                                                                             
      sock = connection.create_connection(                                                           
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^                                                           
    File "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\site-packages\urllib3\util\con 
  nection.py", line 81, in create_connection                                                         
      sock.close()                                                                                   
    File "C:\Users\PULKIT\AppData\Local\Programs\Python\Python312\Lib\socket.py", line 500, in close 
      def close(self):                                                                               
                                                                                                     
  KeyboardInterrupt                                                                                  
  PS C:\Users\PULKIT\Desktop\FORGE_01>  it was not stopping and going on continuosly i had to stop   
  it please rectify the error and make necessary changes in the code "
- **For:** to stop its looping when ollama model not found 
- **Revised?** this is final promt after the previous promt i gave it.
