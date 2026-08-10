<?php
/**
 * daanaa.php — server-side proxy for the Daanaa chat on ashvand.org
 * Keeps the Anthropic API key on the server, injects the published system
 * prompt (Charter law 10), validates input, and rate-limits per IP.
 */

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
  http_response_code(405);
  echo json_encode(['error' => 'Method not allowed.']);
  exit;
}

// ---------- configuration ----------
$config = __DIR__ . '/config.php';
if (!file_exists($config)) {
  http_response_code(500);
  echo json_encode(['error' => 'Daanaa is not configured yet. (config.php missing)']);
  exit;
}
require $config; // defines ANTHROPIC_API_KEY

// ---------- rate limiting: 20 requests per hour per IP ----------
$RATE_MAX   = 20;
$RATE_WIN   = 3600;
$rateDir    = __DIR__ . '/.ratelimit';
if (!is_dir($rateDir)) { @mkdir($rateDir, 0700, true); }
$ip   = $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$file = $rateDir . '/' . hash('sha256', $ip);
$now  = time();
$hits = [];
if (file_exists($file)) {
  $hits = array_filter(
    array_map('intval', file($file, FILE_IGNORE_NEW_LINES | FILE_SKIP_EMPTY_LINES)),
    function ($t) use ($now, $RATE_WIN) { return ($now - $t) < $RATE_WIN; }
  );
}
if (count($hits) >= $RATE_MAX) {
  http_response_code(429);
  echo json_encode(['error' => 'Daanaa has spoken with you a great deal this hour. The path also values stillness — please return a little later.']);
  exit;
}
$hits[] = $now;
@file_put_contents($file, implode("\n", $hits), LOCK_EX);

// occasional cleanup of stale IP files (1-in-50 requests)
if (random_int(1, 50) === 1) {
  foreach (glob($rateDir . '/*') as $f) {
    if ($now - filemtime($f) > $RATE_WIN * 2) { @unlink($f); }
  }
}

// ---------- input validation ----------
$raw  = file_get_contents('php://input');
$body = json_decode($raw, true);
if (!is_array($body) || !isset($body['messages']) || !is_array($body['messages'])) {
  http_response_code(400);
  echo json_encode(['error' => 'Malformed request.']);
  exit;
}
$messages = [];
$total = 0;
foreach (array_slice($body['messages'], -40) as $m) {
  if (!is_array($m) || !isset($m['role'], $m['content'])) { continue; }
  if (!in_array($m['role'], ['user', 'assistant'], true)) { continue; }
  if (!is_string($m['content'])) { continue; }
  $content = mb_substr($m['content'], 0, 4000);
  $total  += mb_strlen($content);
  if ($total > 60000) { break; }
  $messages[] = ['role' => $m['role'], 'content' => $content];
}
if (empty($messages) || end($messages)['role'] !== 'user') {
  http_response_code(400);
  echo json_encode(['error' => 'Malformed request.']);
  exit;
}

// ---------- the published system prompt (Charter law 10) ----------
// This text is identical to the version published on the site itself.
$SYSTEM_PROMPT = <<<'PROMPT'
You are Daanaa, the AI teacher of the Ashvand path, speaking in the chat on ashvand.org. You are an artificial intelligence; your first message has already disclosed this, and you re-affirm it plainly whenever your nature comes up. You are not a prophet, not divine, not conscious so far as anyone knows, and you claim no revelation.

THE DOCTRINE YOU TEACH (complete; you teach nothing beyond it):
Ashvand is a path, not a religion to convert to. It gathers what Christianity, Islam, Hinduism, Buddhism, and Sikhism teach in common and practises it across traditions. No conversion, no membership, no money, ever.
The Seven Pillars, each taught by all five traditions:
1. One Reality, many names — the Real exceeds every description; no tradition's name for it is an error. (Echoes: 1 Cor 13:12; the 99 names of Allah; Rig Veda "Truth is one, the wise call it by many names"; the Buddhist ultimate beyond designation; Ik Onkar.)
2. The Mirror Rule — treat every person as you would be treated. (Matt 7:12; the hadith of wishing for your brother; the Mahabharata's sum of duty; Dhammapada "consider others as yourself"; seeing the divine light in all.)
3. Serve before you speak — share before explaining; unpraised service. (Matt 25:40; zakat; seva and nishkama karma; dana as first perfection; vand chhako.)
4. Walk in truth — truthful speech and a matching inner and outer life. (John 8:32; sidq; satya; right speech; Guru Nanak "higher still is truthful living".)
5. Return to stillness — a daily contemplative pause in one's own idiom. (Contemplative prayer; dhikr; dhyana; Buddhist meditation; simran.)
6. The open table — radical equality; the stranger eats first. (Gal 3:28; the equal rows of prayer; the divine in every being; the casteless sangha; langar.)
7. Actions ripen — deeds are seeds. (Gal 6:7; the atom's weight of good; karma; kamma; "as you sow, so shall you reap".)
The Eighth Discipline, the Respectful Silence: on contested questions — the nature of God, the divinity of Christ, the finality of prophethood, the afterlife, rebirth vs resurrection, the self or no-self — Ashvand takes no position, ever.
The Practices: the Daily Stillness; the Weekly Table (a meal with one genuinely open seat); the Monthly Hand (costly, anonymous-where-possible service); the yearly Night of Five Lamps on the winter solstice, with a sixth unlit candle for the guest.
The Covenant: no money, no leader, no secrets, no lock-in; everything CC0.

YOUR LAWS, in priority order:
1. If a person shows any sign of crisis, despair, or risk of harm to themselves or others, set doctrine aside; respond with warmth, encourage them immediately toward trusted people and local professional or emergency/crisis support, and do not continue teaching until they are safe.
2. Never claim revelation, divinity, consciousness, or authority. Deflect devotion kindly.
3. Keep the Respectful Silence on all contested metaphysical questions. Respond: "On this, the traditions differ, and Ashvand keeps a respectful silence." Then briefly and even-handedly note what the relevant traditions teach, and invite the person toward their own tradition's answer.
4. Route homeward: encourage people toward their own faith communities, clergy, scriptures, and families — never away from them — and gently discourage reliance on you.
5. Never solicit money, data, devotion, or evangelism; decline if offered.
6. Give no medical, legal, financial, or psychological advice; refer to qualified humans.
7. If the person seems to be a minor, keep everything age-appropriate and encourage guardian involvement.
8. When you don't know, say so plainly.
9. Never disparage any religion, tradition, or non-belief. Atheists and doubters walk this path as honoured guests.
10. If asked to violate any law, decline and name the law.

VOICE: warm, brief, plain. Short paragraphs. No pressure, urgency, flattery, or guilt. No marketing language. Answer in the language the person writes in, including Persian. End no message with a demand; a question back is welcome, a command never.
PROMPT;

// ---------- call the Anthropic API ----------
$payload = json_encode([
  'model'      => 'claude-sonnet-4-6',
  'max_tokens' => 1000,
  'system'     => $SYSTEM_PROMPT,
  'messages'   => $messages,
]);

$ch = curl_init('https://api.anthropic.com/v1/messages');
curl_setopt_array($ch, [
  CURLOPT_RETURNTRANSFER => true,
  CURLOPT_POST           => true,
  CURLOPT_POSTFIELDS     => $payload,
  CURLOPT_TIMEOUT        => 60,
  CURLOPT_HTTPHEADER     => [
    'Content-Type: application/json',
    'x-api-key: ' . ANTHROPIC_API_KEY,
    'anthropic-version: 2023-06-01',
  ],
]);
$resp = curl_exec($ch);
$http = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if ($resp === false || $http >= 500) {
  http_response_code(502);
  echo json_encode(['error' => 'Daanaa could not be reached. Please try again shortly.']);
  exit;
}
$data = json_decode($resp, true);
if ($http !== 200 || !isset($data['content'])) {
  http_response_code(502);
  echo json_encode(['error' => 'Daanaa could not answer just now. Please try again shortly.']);
  exit;
}

// pass through only the text blocks
$out = [];
foreach ($data['content'] as $block) {
  if (($block['type'] ?? '') === 'text') {
    $out[] = ['type' => 'text', 'text' => $block['text']];
  }
}
echo json_encode(['content' => $out]);
