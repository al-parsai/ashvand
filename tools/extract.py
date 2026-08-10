"""
index.html -> template.html + i18n/en.json

BeautifulSoup is used ONLY to locate translation units. Every edit is made by
offset against the raw source, so the template is byte-identical to the input
apart from the substitutions themselves. (A bs4 round-trip reorders attributes
and self-closes void tags, which would make the regression diff useless.)
"""
import json, re, sys
from bs4 import BeautifulSoup, Tag

SRC = sys.argv[1]
src = open(SRC, encoding='utf-8').read()
soup = BeautifulSoup(src, 'html.parser')

line_off = [0]
for ln in src.split('\n'):
    line_off.append(line_off[-1] + len(ln) + 1)
def abs_of(tag):
    return line_off[tag.sourceline - 1] + tag.sourcepos

INLINE = {'em','strong','b','i','span','br','sup','sub','small','code','abbr'}
OPAQUE = {'script','style','svg','head','template'}

def end_of_start_tag(i):
    """Offset just past the '>' that closes the start tag beginning at i."""
    j, q = i + 1, None
    while j < len(src):
        c = src[j]
        if q:
            if c == q: q = None
        elif c in '"\'': q = c
        elif c == '>': return j + 1
        j += 1
    raise ValueError('unterminated start tag')

def inner_end(name, start):
    """Offset of the matching '</name'."""
    depth, j = 1, start
    pat = re.compile(r'</?' + re.escape(name) + r'\b', re.I)
    while True:
        m = pat.search(src, j)
        if not m: raise ValueError('unclosed <%s>' % name)
        depth += -1 if m.group().startswith('</') else 1
        if depth == 0: return m.start()
        j = m.end()

def is_unit(tag):
    if tag.name in OPAQUE or not tag.get_text(strip=True): return False
    kids = tag.find_all(True, recursive=False)
    # A run of sibling links or spans is better split than bundled, so a
    # translator never has to preserve an href by hand.
    if len(kids) >= 2 and len({k.name for k in kids}) == 1 and kids[0].name in ('a','span','li'):
        bare = ''.join(s for s in tag.find_all(string=True, recursive=False)).strip()
        if not bare: return False
    return all(k.name in INLINE or k.name == 'a' for k in kids)

units, counters = [], {}
def key_for(node):
    ns = 'page'
    for p in node.parents:
        if isinstance(p, Tag):
            if p.get('id'): ns = p['id']; break
            if p.name in ('nav','header','footer'): ns = p.name; break
    counters[ns] = counters.get(ns, 0) + 1
    return '%s.%02d' % (ns, counters[ns])

def walk(tag):
    for child in tag.find_all(True, recursive=False):
        if child.name in OPAQUE: continue
        if is_unit(child):
            units.append((key_for(child), child))
        else:
            walk(child)
walk(soup.find('body'))

# --- attributes -------------------------------------------------------
attrs = {}
ATTRS = ('placeholder','aria-label','title','alt')
attr_edits = []
for tag in soup.find_all(True):
    if tag.name in ('script','style'): continue
    for a in ATTRS:
        v = tag.get(a)
        if v and re.search(r'[A-Za-z]{3}', v) and ' ' in v.strip():
            k = 'attr.%02d' % (len(attrs) + 1); attrs[k] = v
            attr_edits.append((abs_of(tag), a, v, k))
for sel, key in ((('name','description'), 'meta.description'),
                 (('property','og:title'), 'meta.og_title'),
                 (('property','og:description'), 'meta.og_description')):
    m = soup.find('meta', attrs={sel[0]: sel[1]})
    if m and m.get('content'):
        attrs[key] = m['content']; attr_edits.append((abs_of(m), 'content', m['content'], key))
t = soup.find('title')
if t:
    attrs['meta.title'] = t.get_text()
    units.append(('meta.title', t))

# --- apply edits back-to-front so offsets stay valid -------------------
html_strings = {}
edits = []
for key, tag in units:
    s = abs_of(tag); ist = end_of_start_tag(s); iend = inner_end(tag.name, ist)
    inner = src[ist:iend]
    if not re.search(r'[A-Za-z]', inner): continue
    if key != 'meta.title': html_strings[key] = inner.strip()
    else: attrs['meta.title'] = inner.strip()
    ins = ' data-i18n="%s"' % key if key != 'meta.title' else ''
    edits.append((s, ist, iend, ins, '@@%s@@' % key))

for start, ist, iend, ins, ph in sorted(edits, key=lambda e: -e[0]):
    src = src[:ist - 1] + ins + src[ist - 1:ist] + ph + src[iend:]

for pos, a, v, k in sorted(attr_edits, key=lambda e: -e[0]):
    e = end_of_start_tag(pos)
    seg = src[pos:e].replace('%s="%s"' % (a, v), '%s="@@%s@@"' % (a, k), 1)
    src = src[:pos] + seg + src[e:]

open('template.html','w',encoding='utf-8').write(src)
json.dump({'html': html_strings, 'attr': attrs},
          open('_strings.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('units: %d   attrs: %d' % (len(html_strings), len(attrs)))
