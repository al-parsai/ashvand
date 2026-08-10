# Deploying ashvand.org to SiteGround

## Files in this package
- index.html      — the complete site (chat now calls /daanaa.php)
- daanaa.php      — server-side proxy: holds the API key, injects the Charter
                    system prompt, validates input, rate-limits 20 req/hour/IP
- config.sample.php — rename to config.php, paste your Anthropic API key
- .htaccess       — blocks web access to config.php and .ratelimit/, forces HTTPS

## Steps
1. API key: console.anthropic.com → API Keys → create key.
   Then Settings → Limits: set a monthly spend cap (US$25 is generous to start).
2. SiteGround Site Tools → create the site for ashvand.org.
3. Upload all four files to public_html/ via File Manager (upload .htaccess too —
   enable "show hidden files" to confirm it arrived).
4. Rename config.sample.php → config.php, edit it, paste the key. Set file
   permissions to 600 if the file manager allows.
5. DNS at Netfirms: change the domain's nameservers to the pair shown in your
   SiteGround Site Tools (Site → Dashboard). Propagation: minutes to ~24h.
   (Alternative: keep Netfirms DNS and set an A record to your SiteGround IP
   plus a www CNAME — but nameservers are cleaner.)
6. Once DNS resolves: Site Tools → Security → SSL Manager → install
   Let's Encrypt → enable HTTPS Enforce.
7. Test: load the site, ask Daanaa a question, then ask 21 questions quickly
   from one device to confirm the rate limit message appears.

## Cost expectation
Claude Sonnet, ~1000-token replies, modest system prompt: roughly 1–2 cents
per exchange. The per-IP limit plus your monthly cap bound the worst case.

## Later hardening (optional)
- Put the domain behind Cloudflare (free) for bot filtering and caching.
- Add a Turnstile/CAPTCHA check in daanaa.php if abuse ever appears.
- Keep config.php out of any git repo, ever.

## Update: favicons + voice (v1.1)
Upload/replace in public_html:
  index.html          (replaces existing)
  favicon.ico         (root)
  favicon.svg         (root)
  site.webmanifest    (root)
  icons/              (new folder: icon-192.png, icon-512.png, apple-touch-icon.png)

Voice notes:
- Microphone input uses the browser SpeechRecognition API (Chrome, Edge, Safari).
  Firefox does not support it; the mic button hides itself automatically there.
- Requires HTTPS (already in place) and a one-time permission prompt.
- Read-aloud uses speechSynthesis and is OFF by default — the visitor turns it on.
- Persian is detected by script and switches both recognition and voice to fa-IR,
  subject to the voices installed on the visitor's device.
