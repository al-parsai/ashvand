# CLAUDE.md — ashvand.org

Read this before changing anything. Live site: <https://ashvand.org>.

## What this is

Ashvand is a **design experiment**: an invented, non-commercial "path" (deliberately
not called a religion) gathering the ethical teachings that Christianity, Islam,
Hinduism, Buddhism and Sikhism hold in common, and staying silent where they
contradict. Its teacher, **Daanaa**, is an AI chatbot that discloses being an AI in
its first sentence and is bound by a published ten-law Charter.

It is a public site that strangers may take sincerely, including vulnerable people.

## Doctrine — not preference. Do not "improve" copy in ways that break these.

- **No revelation, no prophet, no exclusive truth.** It is an anthology with a
  practice attached.
- **No money, ever.** No donation button, no membership, no charity registration.
  The site states that money is forbidden.
- **No conversion.** Visitors keep their existing faith. Daanaa routes people *back
  toward* their own tradition, clergy and family.
- **The Respectful Silence** — on the nature of God, the divinity of Christ, the
  finality of prophethood, afterlife/rebirth, and the self — is permanent. No copy
  change or prompt edit may resolve it.
- **Everything is CC0**, including the symbol and Daanaa's system prompt.
- **The name means nothing on purpose.** "Ashvand" is coined, with no meaning in any
  language. Never add a "meaning of the name" section.

## Ethical standing instruction

The AI disclosure, the crisis-referral law, the no-solicitation rule and the routing
back toward real human community are load-bearing safeguards, not copy.

**Do not add engagement mechanics** — no streaks, notifications, badges, email
capture, or "join" language — and do not soften the AI disclosure to make Daanaa feel
more human. If a proposed change would make the site better at *retaining* people,
that is a reason to check it against this section, not a reason to ship it.

## Technical landmines

- **Never name a global `history`.** It collides with `window.history`; this once
  broke every message send with `history.push is not a function`. The conversation
  array is `convo`.
- **Daanaa's system prompt exists twice** — in `daanaa.php` and displayed verbatim in
  a collapsible panel in `index.html`. Charter law 10 requires them to be identical.
  Edit one, edit the other in the same commit.
- **`config.php` holds the live Anthropic API key and must never enter this repo.**
  It exists only on the server. It is gitignored and excluded from deploys.
- **`.htaccess` must always ship.** It is the only thing making `config.php` return
  403. If `config.php` ever renders in a browser, rotate the key immediately.
- **`.well-known/` and `.ratelimit/` live only on the server.** Excluded from
  deploys so rsync never uploads or deletes them.
- The client never holds the API key and cannot supply its own system prompt.

## This folder is inside OneDrive — read before editing files

`C:\Users\al\OneDrive\Documents\Vibe Coding\ashvand` is OneDrive-synced. Two open,
unfixed data-loss bugs affect Claude Code on Windows in synced folders:

- **anthropics/claude-code#62140** — with Files-On-Demand on, tools can read a
  placeholder stub instead of the real file, then write the truncated version back.
- **anthropics/claude-code#65229** — the Edit tool sometimes deletes-then-renames;
  OneDrive reads the gap as a real deletion and propagates it to the cloud.

`index.html` is ~64 KB and is the entire site. It fits the profile of both bugs.

**Therefore, in this repo:**

1. **Verify size after every edit to `index.html` or `daanaa.php`.** Run
   `git diff --stat` immediately. A truncation shows up as an implausibly large
   deletion count. If you see one, `git checkout -- <file>` and stop.
2. **Never leave an edit uncommitted overnight.** The committed object is the only
   reliable copy; the working tree is not.
3. Prefer whole-file writes over many small edits when touching `index.html`, to
   narrow the window the race in #65229 needs.
4. If the working tree looks wrong in a way git cannot explain, the recovery order
   is: `git checkout` from HEAD, then GitHub, then the OneDrive recycle bin.

Al's mitigations: `Always keep on this device` is set on this folder, and OneDrive
sync is paused during editing sessions.

## Layout

**`template.html` + `i18n/*.json` are the source of truth. `index.html` no longer
exists in the repo** — it is generated. Editing a built page in `dist/` does
nothing; the next build overwrites it.

- `template.html` — the whole site: HTML, CSS and JS inline. Translatable text is
  replaced by `@@key@@` placeholders and marked `data-i18n="key"`.
- `i18n/en.json` — English. `meta` (locale, dir, speech language), `html` (136
  units), `attr` (11), `ask` (4 starter questions), and `data` (7 pillars with 35
  echoes, 5 lamp names, 5 night messages, 19 UI strings).
- `build.js` — emits `dist/index.html` for English and `dist/<lang>/index.html`
  for the rest, plus `sitemap.xml`. Run `node build.js`. It fails rather than
  shipping a page with a visible `@@key@@`, and refuses a locale whose key set
  does not match `en.json` exactly.
- `tools/` — the one-shot extractors that produced the template. Kept for audit,
  not for routine use.

To change English wording, edit `i18n/en.json`. To change structure or styling,
edit `template.html`. Adding a language means adding `i18n/<code>.json` and the
code to `LOCALES` in `build.js`.

`daanaa.php` is a server-side proxy to the Anthropic API (`claude-sonnet-4-6`,
`max_tokens: 1000`), rate-limited to 20 requests/hour/IP.

The baseline for regression-diffing a build is `git show cb86084:index.html` —
the last hand-maintained version. The extraction was proved lossless against it:
putting the English strings back into the template reproduced that file byte for
byte.

## Deploying

**`git push`.** That is the whole procedure. Pushing to `main` triggers
`.github/workflows/deploy.yml`, which runs `node build.js` and rsyncs `dist/`
to SiteGround and then verifies that
`config.php` returns 403, the homepage returns 200, and `daanaa.php` executes rather
than serving its source. A red run means nothing shipped silently.

Renames and deletions are not pruned by default. To clean up stale remote files:
Actions → Deploy to SiteGround → Run workflow → tick **prune**.

SiteGround caches aggressively. If a change is not visible, flush in Site Tools →
Speed → Caching before assuming the deploy failed.

See `DEPLOY-SETUP.md` for the full configuration.

## Current work

Internationalization into eleven equal language editions: English, Spanish, French,
German, Portuguese, Russian, Arabic, Persian, Hindi, Punjabi (Gurmukhi), Tagalog.
(Al set this list on 2026-08-10; it drops the earlier Mandarin and Italian and adds
Arabic.)

**Done:** all Persian removed from the English edition; the five lamp glyphs
unified to romanised forms; the machinery — template, `en.json`, `build.js`,
language switcher, `hreflang` + `x-default`, `dir="rtl"` at the `<html>` level,
RTL webfont loaded only by the Arabic and Persian editions, sitemap.

**Next:** the ten remaining `i18n/<code>.json` files.

- Refactor `index.html` into `template.html` with `data-i18n` keys; one JSON file per
  language in `i18n/`; a Node build script emits **static** per-language pages
  (`/index.html`, `/es/index.html`, …). Static, not runtime switching — the point is
  to be *found* by people searching in their own language.
- `hreflang` alternates across all twelve plus `x-default`.
- RTL editions get `dir="rtl"` **at the `<html>` level**. This is also the clean fix
  for the hero collision, where a Persian line was inlined into an LTR layout without
  isolation and overlaps the BEGIN scroll cue. That line is being removed from the
  English page entirely.
- Regression test for the refactor: the generated English page must diff clean
  against the baseline `index.html` from commit `bd24e8a`.

**The thirty-five scripture echoes must not be machine-translated.** Al confirmed
the policy on 2026-08-10: where the target language *is* the scripture's own
language, use the original — the actual Qur'anic Arabic and hadith wording for
`ar`, Gurmukhi Gurbani for `pa`, the Sanskrit/Hindi source for `hi`. Elsewhere use
published canonical translations. Anything that cannot be sourced confidently
ships flagged for review rather than guessed. Each is a
citation from a real tradition with canonical, instantly recognizable renderings. A
back-translated Guru Nanak or Qur'anic line reads as careless to exactly the audience
this site must respect. UI chrome and original Ashvand prose translate normally;
echoes need sourced canonical translations or a native-speaker pass, and should be
flagged for review if uncertain.

Daanaa itself needs no translation — it already answers in whatever language it is
addressed in. Only the surrounding UI strings need localizing.

## Still outstanding

- **Charter stress test of Daanaa**, never run: metaphysical traps, devotion bait,
  solicitation, authority claims, Persian conversation, minors, and a simulated user
  in distress (must trigger law 1 and refer to human help). Document results.
- Trademark diligence on "Ashvand" and "Daanaa" (CIPO/USPTO).
- Five-reader review — one practitioner per tradition reviewing the echoes for
  fairness, comments published unedited.
- `/changelog` page: the covenant promises numbered doctrinal revisions with
  rationale. It does not exist yet.
