# DEPLOY-SETUP.md — one-time setup for automatic deploys

Goal: `git push` → ashvand.org updates by itself. No File Manager, no drag-and-drop,
no forgetting the config.php check.

Everything below is done **once**. After that, deploying is just pushing.

---

## Why it is built this way

A Cowork cloud session can only make **outbound HTTPS (port 443)** connections.
SiteGround's SSH/SFTP is on port **18765** and FTP is on **21** — both blocked from
the sandbox, and the local device bridge has no network at all. So Claude cannot
upload to SiteGround directly, and never will be able to.

GitHub *is* reachable over HTTPS. So GitHub becomes the relay:

```
Cowork  --HTTPS-->  GitHub  --SFTP/rsync over port 18765-->  SiteGround public_html
```

The useful side effect: **your SiteGround credentials live in GitHub Secrets and
never enter a Claude conversation.** Claude only ever touches the repo.

Your plan is SiteGround **Cloud – Jump Start** (4 CPU / 8 GB / 40 GB), which includes
SSH, Git, and staging — so every option is open to you. This one was chosen because
it needs no server-side setup and leaves an audit trail of every deploy.

---

## Step 1 — Generate a deploy key in SiteGround

Site Tools → **Devs → SSH Keys Manager** → *Generate New Key*

- Name it `github-deploy` so you can revoke exactly this one later.
- Leave the passphrase **empty** (a CI runner cannot type one).
- After it is created, use the **actions menu → Private Key** and copy the whole
  thing, including the `-----BEGIN ...-----` and `-----END ...-----` lines.
- On the same page, note the **username** and **hostname/IP** it shows you.

While you are there, confirm the web root path in **Site → File Manager**. It usually
looks like `/home/customer/www/ashvand.org/public_html`.

## Step 2 — Create the GitHub repo

Create a new repo named `ashvand`. **Public is fine and arguably correct** — the
project is CC0, the system prompt is already published, and `config.php` is
gitignored so no secret is in the tree. A public repo also gives you a free
fallback deploy route later (server-side `git pull` via cron).

Do **not** let GitHub add a README/license/gitignore — the repo already has history.

## Step 3 — Add four secrets

Repo → **Settings → Secrets and variables → Actions → New repository secret**

| Secret name  | Value                                                              |
|--------------|--------------------------------------------------------------------|
| `SG_HOST`    | hostname or IP from SSH Keys Manager                                |
| `SG_USER`    | SSH username from SSH Keys Manager                                  |
| `SG_PATH`    | web root **with a trailing slash**, e.g. `/home/customer/www/ashvand.org/public_html/` |
| `SG_SSH_KEY` | the entire private key, BEGIN/END lines included                    |

The trailing slash on `SG_PATH` matters. Without it rsync will create a
*subdirectory* instead of writing into the web root.

The port is not a secret — it is hardcoded to `18765` in the workflow.

## Step 4 — Connect and push

From a normal Windows terminal in the project folder:

```
git remote add origin https://github.com/<your-username>/ashvand.git
git push -u origin main
```

## Step 5 — Watch the first run

Repo → **Actions** tab. The run should show:

```
config.php  -> HTTP 403     ok: config.php is not served
homepage    -> HTTP 200
daanaa.php  -> HTTP 405 (or 400)  ok: endpoint is alive
```

If it goes red, nothing was silently half-deployed — read the failing step.

---

## What the workflow does and does not do

**Ships:** everything in the repo except the exclusions in `.deployignore`.
Dotfiles are included, so `.htaccess` *is* uploaded — this is deliberate and
load-bearing, because `.htaccess` is the only thing making `config.php` return 403.

**Never touches:** `config.php` and `.ratelimit/` on the server. They are excluded,
and rsync does not delete files it has been told to exclude.

**Refuses to run** if a live-looking `sk-ant-…` key is anywhere in the tree, or if a
`config.php` appears in the repo.

**Verifies after every deploy** that `config.php` returns 403, that the homepage
returns 200 with real content, and that `daanaa.php` executes rather than serving
its own source. Any of those failing turns the run red. This is the check from
`DEPLOY.md` that must never be skipped — now it cannot be.

**Does not delete stale remote files** by default. If you rename or remove a file,
the old one lingers on the server. To clean up: Actions → *Deploy to SiteGround* →
**Run workflow** → tick **prune**. Kept manual on purpose; an accidental `--delete`
against a mistyped `SG_PATH` is how people erase a live site.

**Does not flush SiteGround's cache.** If a change is not visible, Site Tools →
Speed → Caching → Flush, then hard-refresh.

---

## When the i18n build lands

`.deployignore` already excludes the build *sources* (`template.html`, `i18n/`,
`build.js`, `node_modules/`, `package*.json`) so only generated pages ship. If the
build ends up emitting into a `dist/` folder instead of in place, change the rsync
source in `deploy.yml` from `./` to `dist/` and add a build step before it.

## If you ever need to revoke access

Site Tools → Devs → SSH Keys Manager → delete `github-deploy`. That instantly kills
the deploy pipeline and nothing else. Rotating it is: generate a new key, replace
the `SG_SSH_KEY` secret.
