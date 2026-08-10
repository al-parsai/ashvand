"""
Pass 2: lift the JS data and runtime strings out of template.html.

SYSTEM_PROMPT is deliberately NOT touched. Charter law 10 requires the copy
shown on the page to be identical to the one daanaa.php sends to the model,
and that one is English. Every edition shows it verbatim in English.
"""
import json, re, sys

tpl = open('template.html', encoding='utf-8').read()
data = {}

def cut(pattern, repl, label, flags=0):
    global tpl
    m = re.search(pattern, tpl, flags)
    assert m, 'NOT FOUND: ' + label
    tpl = tpl[:m.start()] + repl + tpl[m.end():]
    return m

# ---- PILLARS: 7 pillars x {title, creed, 5 echoes} -------------------
m = re.search(r'var PILLARS=\[\n(.*?)\n\];', tpl, re.S)
assert m, 'PILLARS'
block = m.group(1)
pillars = []
for pm in re.finditer(r'\{t:"((?:[^"\\]|\\.)*)",c:"((?:[^"\\]|\\.)*)",\s*e:\[(.*?)\]\}', block, re.S):
    echoes = [{'tradition': a, 'text': b, 'cite': c} for a, b, c in
              re.findall(r'\["((?:[^"\\]|\\.)*)","((?:[^"\\]|\\.)*)","((?:[^"\\]|\\.)*)"\]', pm.group(3))]
    pillars.append({'title': pm.group(1), 'creed': pm.group(2), 'echoes': echoes})
assert len(pillars) == 7, len(pillars)
assert sum(len(p['echoes']) for p in pillars) == 35
data['pillars'] = pillars
tpl = tpl[:m.start()] + 'var PILLARS=@@json:data.pillars@@;' + tpl[m.end():]

# ---- the five lamps --------------------------------------------------
m = cut(r'var LAMP_NAMES=\[[^\]]*\];', 'var LAMP_NAMES=@@json:data.lamps@@;', 'LAMP_NAMES')
data['lamps'] = json.loads(re.search(r'\[[^\]]*\]', m.group()).group())

# ---- night-of-five-lamps messages -----------------------------------
m = cut(r'var msgs=\[[^\]]*\];', 'var msgs=@@json:data.night.messages@@;', 'night messages')
data.setdefault('night', {})['messages'] = json.loads(re.search(r'\[[^\]]*\]', m.group()).group())

ui = {}
def s(key, pattern, label, group=1, flags=0):
    """Replace a JS string literal with a UI.<key> reference."""
    global tpl
    m = re.search(pattern, tpl, flags)
    assert m, 'NOT FOUND: ' + label
    ui[key] = m.group(group).replace('\\u2019', '\u2019').replace("\\'", "'")
    tpl = tpl[:m.start(group) - 1] + 'UI.' + key + tpl[m.end(group) + 1:]


def s_embed(key, pattern, label, group=1, flags=0):
    """Replace text embedded inside a larger JS string literal."""
    global tpl
    m = re.search(pattern, tpl, flags)
    assert m, 'NOT FOUND: ' + label
    ui[key] = m.group(group).replace('\\u2019', '\u2019').replace("\\'", "'")
    tpl = tpl[:m.start(group)] + "'+UI." + key + "+'" + tpl[m.end(group):]

s('lightLamp',      r"'(Light the lamp of )'\+n", 'lamp aria')
s('guestCandleAria',r"'(The guest\\u2019s candle — enabled when all five lamps are lit)'", 'guest aria')
s_embed('guestCandle', r'<span class="nm">(the guest\\u2019s candle)</span>', 'guest label')
s('guestLit',       r'"(Light and truth\. The circle was never closed[^"]*)"', 'guest lit message')
s('stopListening',  r"'(Stop listening)'", 'stop listening')
s('listening',      r"'(Listening — speak now, then pause\.)'", 'listening note')
s('micBlocked',     r"'(Microphone permission is blocked[^']*)'", 'mic blocked')
s('micNothing',     r"'(Could not hear anything[^']*)'", 'mic heard nothing')
s('speakQuestion',  r"'(Speak your question)'", 'mic idle aria')
s('voiceOn',        r"'(Voice on)'", 'voice on')
s('voiceOff',       r"'(Voice off)'", 'voice off')
s('considering',    r"'(Daanaa is considering)'", 'typing aria')
s('greeting',       r'addMsg\("((?:[^"\\]|\\.)*)"', 'Daanaa greeting')
s('errEmpty',       r"'(Daanaa returned no words[^']*)'", 'empty reply')
s('errInterrupted', r"'(Something interrupted the reply[^']*)'", 'interrupted')
s('errConnection',  r"'(The connection to Daanaa failed[^']*)'", 'connection failed')
data['ui'] = ui

# ---- speech locale: was hardcoded to Persian ------------------------
cut(r"return /\[\\u0600-\\u06FF\]/\.test\(t\) \? 'fa-IR' : 'en-US';",
    "return /[\\u0600-\\u06FF]/.test(t) ? UI.rtlSpeechLang : UI.speechLang;", 'langOf')
cut(r"recog\.lang = langOf\(q\.value\) === 'fa-IR' \? 'fa-IR' : \(navigator\.language \|\| 'en-US'\);",
    "recog.lang = langOf(q.value);", 'recog.lang')
tpl = tpl.replace('var PILLARS=', 'var UI=@@json:data.ui@@;\nvar PILLARS=', 1)

# ---- starter questions: the text actually sent to Daanaa ------------
asks = {}
def ask_sub(m):
    k = 'ask.%02d' % (len(asks) + 1); asks[k] = m.group(1)
    return "ask('@@%s@@')" % k
tpl, n = re.subn(r"ask\('((?:[^'\\]|\\.)*)'\)", ask_sub, tpl)
print('starter questions lifted:', n)

# The pillar data now uses readable keys so a translator sees title/creed/
# echoes rather than t/c/e[0..2]. Update the code that consumes it.
RESHAPE = [
 ("'</span><span class=\"t\">'+p.t+'</span>'", "'</span><span class=\"t\">'+p.title+'</span>'"),
 ("plTitle.textContent=PILLARS[i].t;",           "plTitle.textContent=PILLARS[i].title;"),
 ("plCreed.textContent=PILLARS[i].c;",           "plCreed.textContent=PILLARS[i].creed;"),
 ("PILLARS[i].e.forEach(function(e,j){",         "PILLARS[i].echoes.forEach(function(e,j){"),
 ("t.className='echo-tab';t.textContent=e[0];",  "t.className='echo-tab';t.textContent=e.tradition;"),
 ("var e=PILLARS[curP].e[j];",                   "var e=PILLARS[curP].echoes[j];"),
 ("echoText.textContent=e[1];",                  "echoText.textContent=e.text;"),
 ("echoCite.textContent=e[0]+' — '+e[2];",       "echoCite.textContent=e.tradition+' — '+e.cite;"),
]
for old, new in RESHAPE:
    assert old in tpl, 'RESHAPE target missing: ' + old
    tpl = tpl.replace(old, new, 1)

# ---- page chrome the build fills in ---------------------------------
# Markers must be injected here, not by hand, so re-running the pipeline
# reproduces template.html exactly.
old = '<meta property="og:url" content="https://ashvand.org/">'
assert old in tpl, 'og:url anchor'
tpl = tpl.replace(old, old + '\n<!--HREFLANG-->', 1)

old = '      <a class="cta" href="#daanaa" data-i18n="nav.07">@@nav.07@@</a>\n'
assert old in tpl, 'nav cta anchor'
tpl = tpl.replace(old, old + '      <!--LANGSWITCH-->\n', 1)

anchor = '.links a:hover{color:var(--teal-deep)}'
assert anchor in tpl, 'nav css anchor'
tpl = tpl.replace(anchor, anchor + """
.lang{position:relative;margin-left:2px}
.lang>summary{list-style:none;cursor:pointer;font-family:var(--sans);font-size:12px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);padding:7px 12px;border:1px solid var(--hair);border-radius:999px;display:flex;align-items:center;gap:8px;white-space:nowrap;transition:color .25s,border-color .25s}
.lang>summary::-webkit-details-marker{display:none}
.lang>summary:hover{color:var(--teal-deep);border-color:var(--teal-deep)}
.lang>summary .chev{width:7px;height:7px;border-right:1.2px solid currentColor;border-bottom:1.2px solid currentColor;transform:rotate(45deg) translateY(-2px);transition:transform .25s}
.lang[open]>summary .chev{transform:rotate(-135deg) translateY(1px)}
.lang-menu{position:absolute;top:calc(100% + 12px);inset-inline-end:0;background:var(--parchment-2);border:1px solid var(--hair);border-radius:14px;padding:8px;min-width:196px;display:grid;gap:1px;box-shadow:0 20px 48px rgba(12,26,30,.15);z-index:60;max-height:min(70vh,520px);overflow:auto}
.lang-menu a{font-family:var(--sans);font-size:14px;font-weight:400;letter-spacing:0;text-transform:none;padding:9px 12px;border-radius:9px;color:var(--ink-soft);display:block;white-space:nowrap}
.lang-menu a:hover{background:var(--teal-mist);color:var(--teal-deep)}
.lang-menu a[aria-current="true"]{color:var(--teal-deep);font-weight:500}
html[dir=rtl] body{font-family:var(--fa)}
html[dir=rtl] .lede,html[dir=rtl] .echo-quote p{text-align:right}""", 1)

open('template.html', 'w', encoding='utf-8').write(tpl)
json.dump({'data': data, 'ask': asks}, open('_data.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('pillars: %d  echoes: %d  lamps: %d  night msgs: %d  ui strings: %d'
      % (len(pillars), sum(len(p['echoes']) for p in pillars), len(data['lamps']),
         len(data['night']['messages']), len(ui)))
