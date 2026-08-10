#!/usr/bin/env node
/**
 * Ashvand static i18n build.
 *
 *   template.html + i18n/<loc>.json  ->  dist/index.html, dist/<loc>/index.html
 *
 * Static pages, not runtime switching: the point is to be *found* by someone
 * searching in their own language, which needs real indexable URLs.
 *
 * Fails loudly on any key mismatch. A page that silently renders "@@nav.03@@"
 * to a visitor is worse than a red build.
 */
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const DIST = path.join(ROOT, 'dist');
const SITE = 'https://ashvand.org';

/** Order controls the switcher menu. English first, then by native name. */
const LOCALES = ['en','es','fr','de','pt','ru','ar','fa','hi','pa','tl'];
const RTL = new Set(['ar','fa']);
/** Webfont covering Arabic and Persian; only requested by RTL editions. */
const RTL_FONT =
  '<link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600&display=swap" rel="stylesheet">';

const read = p => fs.readFileSync(p, 'utf8');
const die = m => { console.error('✗ ' + m); process.exit(1); };

const template = read(path.join(ROOT, 'template.html'));

const locales = {};
for (const loc of LOCALES) {
  const f = path.join(ROOT, 'i18n', loc + '.json');
  if (!fs.existsSync(f)) { console.warn(`  – ${loc}: no i18n/${loc}.json yet, skipping`); continue; }
  try { locales[loc] = JSON.parse(read(f)); }
  catch (e) { die(`i18n/${loc}.json is not valid JSON: ${e.message}`); }
}
if (!locales.en) die('i18n/en.json is required; it is the reference for every other locale.');

const urlFor = loc => (loc === 'en' ? '/' : `/${loc}/`);

/**
 * Resolve a placeholder key against a locale object.
 * The flat maps are checked first, because their keys contain dots
 * ("nav.02", "meta.description") and would otherwise be mistaken for paths.
 */
function lookup(obj, dotted) {
  for (const g of ['html', 'attr', 'ask']) if (obj[g] && dotted in obj[g]) return obj[g][dotted];
  return dotted.split('.').reduce((o, k) => (o == null ? o : o[k]), obj);
}

const KEY_RE = /@@(json:)?([\w.]+)@@/g;
const templateKeys = new Set();
for (const m of template.matchAll(KEY_RE)) templateKeys.add((m[1] || '') + m[2]);

function flatKeys(o) {
  const out = new Set();
  for (const g of ['html','attr','ask']) for (const k of Object.keys(o[g] || {})) out.add(`${g}.${k}`);
  return out;
}

/** Every locale must answer exactly the keys en.json does — no more, no less. */
function checkParity(loc) {
  const a = flatKeys(locales.en), b = flatKeys(locales[loc]);
  const missing = [...a].filter(k => !b.has(k));
  const extra   = [...b].filter(k => !a.has(k));
  if (missing.length) die(`${loc}: missing ${missing.length} key(s), e.g. ${missing.slice(0,4).join(', ')}`);
  if (extra.length)   die(`${loc}: ${extra.length} key(s) not in en.json, e.g. ${extra.slice(0,4).join(', ')}`);
  const en = locales.en.data, l = locales[loc].data;
  if (l.pillars.length !== en.pillars.length) die(`${loc}: ${l.pillars.length} pillars, expected ${en.pillars.length}`);
  l.pillars.forEach((p, i) => {
    if (p.echoes.length !== en.pillars[i].echoes.length)
      die(`${loc}: pillar ${i+1} has ${p.echoes.length} echoes, expected ${en.pillars[i].echoes.length}`);
  });
  if (l.lamps.length !== en.lamps.length) die(`${loc}: expected ${en.lamps.length} lamp names`);
  for (const k of Object.keys(en.ui)) if (!(k in l.ui)) die(`${loc}: data.ui.${k} is missing`);
}

function hreflang(current) {
  const out = [`<link rel="canonical" href="${SITE}${urlFor(current)}">`];
  for (const loc of LOCALES) {
    if (!locales[loc]) continue;
    out.push(`<link rel="alternate" hreflang="${locales[loc].meta.htmlLang}" href="${SITE}${urlFor(loc)}">`);
  }
  out.push(`<link rel="alternate" hreflang="x-default" href="${SITE}/">`);
  return out.join('\n');
}

function switcher(current) {
  const cur = locales[current].meta;
  const items = LOCALES.filter(l => locales[l]).map(l => {
    const m = locales[l].meta;
    const here = l === current ? ' aria-current="true"' : '';
    return `<a href="${urlFor(l)}" lang="${m.htmlLang}" hreflang="${m.htmlLang}"${here}>${m.nativeName}</a>`;
  }).join('');
  const label = locales[current].data.ui.langLabel || 'Language';
  return `<details class="lang"><summary aria-label="${label}">` +
         `<span>${cur.nativeName}</span><span class="chev" aria-hidden="true"></span></summary>` +
         `<div class="lang-menu">${items}</div></details>`;
}

function render(loc) {
  const L = locales[loc], meta = L.meta;
  const ui = { ...L.data.ui, speechLang: meta.speechLang, rtlSpeechLang: meta.rtlSpeechLang };
  const data = { ...L.data, ui };

  let out = template.replace(KEY_RE, (full, isJson, key) => {
    if (isJson) {
      const v = key === 'data.ui' ? ui : lookup({ data }, key);
      if (v === undefined) die(`${loc}: no value for ${key}`);
      return JSON.stringify(v);
    }
    const v = lookup(L, key);
    if (v === undefined || v === null || v === '') die(`${loc}: no value for ${key}`);
    return String(v);
  });

  // data-i18n is a build-time hook only; nothing reads it at runtime.
  out = out.replace(/ data-i18n="[\w.]+"/g, '');
  out = out.replace('<html lang="en">', `<html lang="${meta.htmlLang}" dir="${meta.dir}">`);
  out = out.replace('<!--HREFLANG-->', hreflang(loc));
  out = out.replace('<!--LANGSWITCH-->', switcher(loc));
  if (RTL.has(loc)) out = out.replace('</head>', RTL_FONT + '\n</head>');

  const left = out.match(KEY_RE);
  if (left) die(`${loc}: ${left.length} placeholder(s) survived, e.g. ${left[0]}`);
  return out;
}

// ---- go ---------------------------------------------------------------
try {
  fs.rmSync(DIST, { recursive: true, force: true });
} catch (e) {
  // Some environments (notably the Cowork device bridge) refuse unlink.
  // Files are overwritten anyway; only a removed locale could go stale.
  console.warn(`  ! could not clear dist/ (${e.code}); files will be overwritten in place`);
}
fs.mkdirSync(DIST, { recursive: true });

const built = [];
for (const loc of LOCALES) {
  if (!locales[loc]) continue;
  if (loc !== 'en') checkParity(loc);
  const dir = loc === 'en' ? DIST : path.join(DIST, loc);
  fs.mkdirSync(dir, { recursive: true });
  const html = render(loc);
  fs.writeFileSync(path.join(dir, 'index.html'), html);
  built.push(loc);
  console.log(`  ✓ ${urlFor(loc).padEnd(6)} ${meta_dir(loc)}  ${(html.length/1024).toFixed(1)} KB`);
}
function meta_dir(loc){ return locales[loc].meta.dir.toUpperCase(); }

// static assets ride along unchanged
for (const f of ['daanaa.php','.htaccess','favicon.ico','favicon.svg','site.webmanifest'])
  if (fs.existsSync(path.join(ROOT, f))) fs.copyFileSync(path.join(ROOT, f), path.join(DIST, f));
if (fs.existsSync(path.join(ROOT, 'icons')))
  fs.cpSync(path.join(ROOT, 'icons'), path.join(DIST, 'icons'), { recursive: true });

// a sitemap costs nothing and is the entire point of static language pages
fs.writeFileSync(path.join(DIST, 'sitemap.xml'),
  '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
  built.map(l => `  <url><loc>${SITE}${urlFor(l)}</loc></url>`).join('\n') + '\n</urlset>\n');

console.log(`\nBuilt ${built.length} edition(s): ${built.join(', ')}`);
