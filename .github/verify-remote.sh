#!/bin/bash
# Runs ON the SiteGround server, piped in over SSH by the deploy workflow.
# This is the authoritative post-deploy check: it is not subject to the bot
# protection layer that intercepts requests from GitHub's runner IPs.
#
# Usage: ssh ... 'bash -s' -- /path/to/public_html/ < verify-remote.sh

set -u
root="${1:-}"
[ -n "$root" ] || { echo "FAIL    no web root passed"; exit 1; }
cd "$root" || { echo "FAIL    cannot enter $root"; exit 1; }

fail=0
note() { printf '%-8s %s\n' "$1" "$2"; }

# Files that must exist and be non-empty after a deploy.
for f in .htaccess index.html daanaa.php site.webmanifest; do
  if [ -s "$f" ]; then note ok "$f"; else note MISSING "$f"; fail=1; fi
done

# The secret. rsync excludes it, so a deploy must never disturb it.
if [ -s config.php ]; then
  note ok "config.php present and non-empty"
else
  note FAIL "config.php is missing or empty -- the site's chat is broken"
  fail=1
fi

# Let's Encrypt challenge directory. Excluded from deploys; a prune bug
# would show up here first.
if [ -d .well-known ]; then note ok ".well-known/"; else note WARN ".well-known/ absent"; fi

# The rule that makes config.php return 403. If this is gone, the API key
# is one HTTP request from being public.
if grep -q 'Require all denied' .htaccess && grep -q 'config.php' .htaccess; then
  note ok ".htaccess still denies config.php"
else
  note FAIL ".htaccess no longer denies config.php -- ROTATE THE API KEY"
  fail=1
fi

# Repo plumbing must never reach the web root. These are a hard failure:
# .git would expose the full history, config.sample.php maps the config
# layout, and the rest are simply not web content.
for f in .git .github .vscode .gitignore .deployignore .gitattributes config.sample.php; do
  if [ -e "$f" ]; then note LEAKED "$f must not be on the server"; fail=1; fi
done

# Stray documentation. Publicly readable and pointless to serve, but not
# worth blocking a deploy over -- these predate the pipeline and rsync no
# longer uploads them. Delete them in File Manager when convenient.
for f in *.md; do
  [ -e "$f" ] || continue
  note WARN "$f is served publicly at /$f -- safe to delete"
done

exit $fail
