<?php
/* BioMarket Pulse — backend for Deep Dive, Ask the Pulse and live PubMed lists.
 * Upload next to index.html and config.php. Your API key stays in config.php on the server.
 *
 * Actions (POST JSON {action, ...}):
 *   status                     -> what is switched on
 *   pm_search {query,...}      -> PubMed search (ids + total count)
 *   pm_meta {pmids}            -> PubMed article details
 *   deepdive {term}            -> company/sector JSON (Claude)
 *   ask {turns}                -> answer grounded in today's edition (Claude, with PubMed tool)
 *   br_bio                     -> Brazil biologicals registry (MAPA AGROFIT via Embrapa AgroAPI), refreshed daily
 *
 * Command line (Hostinger cron, once a day):  php /path/to/public_html/api.php sync
 */
declare(strict_types=1);
@set_time_limit(170);
ignore_user_abort(true);
header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

/* Settings live OUTSIDE the website folder so site updates never touch your API key:
 * put bmp-config.php one level above public_html. A config.php next to this file also works. */
$C = null;
foreach ([dirname(__DIR__) . '/bmp-config.php', __DIR__ . '/config.php'] as $cf) if (is_file($cf)) { $C = require $cf; break; }
if (!is_array($C)) $C = [];
$C += [
  'ANTHROPIC_API_KEY' => '', 'DEEPDIVE_MODEL' => 'claude-sonnet-5-5', 'ASK_MODEL' => 'claude-sonnet-5-5',
  'MONTHLY_BUDGET_USD' => 10, 'DEEPDIVES_PER_VISITOR_PER_DAY' => 5, 'ASKS_PER_VISITOR_PER_DAY' => 20,
  'CLAUDE_CALLS_PER_HOUR_SITEWIDE' => 60, 'DEEPDIVE_CACHE_HOURS' => 24, 'NCBI_API_KEY' => '', 'NCBI_EMAIL' => '', 'AGROAPI_KEY' => '', 'AGROAPI_SECRET' => '',
  'PRICES' => [
    'claude-sonnet-5-5' => ['in' => 2.00, 'out' => 10.00, 'cache_read_mult' => 0.05],
    'claude-haiku-5-5'  => ['in' => 0.10, 'out' => 0.50,  'cache_read_mult' => 0.10],
    'claude-opus-5-5'   => ['in' => 4.00, 'out' => 20.00, 'cache_read_mult' => 0.05],
  ],
];
$C += [
  'ANTHROPIC_URL' => 'https://api.anthropic.com/v1/messages',
  'NCBI_URL'      => 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/',
];
if (getenv('BMP_ANTHROPIC_URL')) $C['ANTHROPIC_URL'] = getenv('BMP_ANTHROPIC_URL');
if (getenv('BMP_NCBI_URL'))      $C['NCBI_URL']      = getenv('BMP_NCBI_URL');

function out(array $a, int $code = 200): never { http_response_code($code); echo json_encode($a, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES); exit; }
function fail(string $code, int $http = 400, array $extra = []): never { out(['ok' => false, 'error' => $code] + $extra, $http); }

/* ---------- storage (outside the web root when possible) ---------- */
function data_dir(): string {
  static $d = null; if ($d) return $d;
  foreach ([dirname(__DIR__) . '/bmp-data', __DIR__ . '/bmp-data'] as $cand) {
    if ((is_dir($cand) || @mkdir($cand, 0700, true)) && is_writable($cand)) {
      if (str_starts_with($cand, __DIR__) && !file_exists("$cand/.htaccess")) @file_put_contents("$cand/.htaccess", "Require all denied\nDeny from all\n");
      foreach (['cache', 'limits'] as $s) if (!is_dir("$cand/$s")) @mkdir("$cand/$s", 0700, true);
      return $d = $cand;
    }
  }
  fail('storage_unavailable', 500);
}
/* Atomically read-modify-write a small JSON file. */
function with_json(string $path, callable $fn) {
  $fh = fopen($path, 'c+'); if (!$fh) fail('storage_unavailable', 500);
  flock($fh, LOCK_EX);
  $raw = stream_get_contents($fh); $v = $raw ? (json_decode($raw, true) ?: []) : [];
  [$v, $ret] = $fn($v);
  ftruncate($fh, 0); rewind($fh); fwrite($fh, json_encode($v)); fflush($fh);
  flock($fh, LOCK_UN); fclose($fh);
  return $ret;
}
function cache_get(string $key, int $ttl) {
  $f = data_dir() . '/cache/' . sha1($key) . '.json';
  if (!is_file($f) || filemtime($f) < time() - $ttl) return null;
  $v = json_decode((string)@file_get_contents($f), true); return $v === null ? null : $v;
}
function cache_put(string $key, $val): void {
  @file_put_contents(data_dir() . '/cache/' . sha1($key) . '.json', json_encode($val, JSON_UNESCAPED_UNICODE), LOCK_EX);
  if (mt_rand(1, 50) === 1) foreach (glob(data_dir() . '/cache/*.json') ?: [] as $f) if (filemtime($f) < time() - 3 * 86400) @unlink($f);
}

/* ---------- who is asking, and limits ---------- */
function visitor(): string {
  $ip = $_SERVER['REMOTE_ADDR'] ?? '0';
  foreach (['HTTP_CF_CONNECTING_IP', 'HTTP_X_FORWARDED_FOR'] as $h) if (!empty($_SERVER[$h])) { $ip = trim(explode(',', $_SERVER[$h])[0]); break; }
  return substr(hash('sha256', $ip . '|' . __DIR__), 0, 20);
}
/* Count one use of $kind for this visitor today; false if over $max. */
function take(string $kind, int $max): bool {
  $f = data_dir() . '/limits/' . date('Y-m-d') . '.json';
  if (mt_rand(1, 30) === 1) foreach (glob(data_dir() . '/limits/*.json') ?: [] as $g) if (filemtime($g) < time() - 3 * 86400) @unlink($g);
  return with_json($f, function ($v) use ($kind, $max) {
    $k = $kind . ':' . visitor(); $n = $v[$k] ?? 0;
    if ($n >= $max) return [$v, false];
    $v[$k] = $n + 1; return [$v, true];
  });
}
function spend_file(): string { return data_dir() . '/spend-' . date('Y-m') . '.json'; }
function spent(): float { $v = json_decode((string)@file_get_contents(spend_file()), true) ?: []; return (float)($v['usd'] ?? 0); }
function claude_open(): ?string {
  global $C;
  if (!trim((string)$C['ANTHROPIC_API_KEY'])) return 'not_configured';
  if (spent() >= (float)$C['MONTHLY_BUDGET_USD']) return 'budget_exhausted';
  return null;
}
function hourly_ok(): bool {
  global $C; $f = data_dir() . '/hourly.json'; $h = date('Y-m-d-H');
  return with_json($f, function ($v) use ($h, $C) {
    if (($v['h'] ?? '') !== $h) $v = ['h' => $h, 'n' => 0];
    if ($v['n'] >= (int)$C['CLAUDE_CALLS_PER_HOUR_SITEWIDE']) return [$v, false];
    $v['n']++; return [$v, true];
  });
}
function record_cost(string $model, array $u): void {
  global $C; $p = $C['PRICES'][$model] ?? ['in' => 4, 'out' => 20, 'cache_read_mult' => 0.1];
  $usd = (($u['input_tokens'] ?? 0) * $p['in']
        + ($u['cache_creation_input_tokens'] ?? 0) * $p['in'] * 2.0   // 1-hour cache writes
        + ($u['cache_read_input_tokens'] ?? 0) * $p['in'] * $p['cache_read_mult']
        + ($u['output_tokens'] ?? 0) * $p['out']) / 1e6;
  with_json(spend_file(), function ($v) use ($usd) { $v['usd'] = round(($v['usd'] ?? 0) + $usd, 6); $v['calls'] = ($v['calls'] ?? 0) + 1; return [$v, null]; });
}

/* ---------- HTTP ---------- */
function http(string $url, ?string $body = null, array $headers = [], int $timeout = 30): array {
  $ch = curl_init($url);
  curl_setopt_array($ch, [CURLOPT_RETURNTRANSFER => true, CURLOPT_TIMEOUT => $timeout, CURLOPT_CONNECTTIMEOUT => 10,
    CURLOPT_HTTPHEADER => $headers, CURLOPT_USERAGENT => 'BioMarketPulse/1.0']);
  if ($body !== null) { curl_setopt($ch, CURLOPT_POST, true); curl_setopt($ch, CURLOPT_POSTFIELDS, $body); }
  $res = curl_exec($ch); $code = (int)curl_getinfo($ch, CURLINFO_HTTP_CODE); curl_close($ch);
  return [$code, $res === false ? '' : (string)$res];
}

/* ---------- PubMed (NCBI E-utilities) ---------- */
function ncbi(string $tool, array $q, int $ttl): string {
  global $C;
  $q += ['db' => 'pubmed', 'tool' => 'biomarketpulse'];
  if ($C['NCBI_API_KEY']) $q['api_key'] = $C['NCBI_API_KEY'];
  if ($C['NCBI_EMAIL'])   $q['email']   = $C['NCBI_EMAIL'];
  $url = $C['NCBI_URL'] . $tool . '?' . http_build_query($q);
  $key = 'ncbi|' . $url;
  if (($hit = cache_get($key, $ttl)) !== null) return $hit['b'];
  for ($i = 0; $i < 3; $i++) {
    [$code, $body] = http($url, null, [], 20);
    if ($code === 200 && $body !== '') { cache_put($key, ['b' => $body]); return $body; }
    usleep(400000 * ($i + 1));
  }
  throw new RuntimeException('pubmed_unavailable');
}
function ymd_ok(?string $d): ?string { $d = trim((string)$d); return preg_match('~^\d{4}(/\d{2}(/\d{2})?)?$~', $d) ? $d : null; }
function pm_search(array $a, int $ttl = 21600): array {
  $term = trim((string)($a['query'] ?? '')); if ($term === '' || strlen($term) > 1500) throw new InvalidArgumentException('bad_query');
  $q = ['term' => $term, 'retmode' => 'json', 'retmax' => max(1, min(20, (int)($a['max_results'] ?? 10)))];
  $q['sort'] = ($a['sort'] ?? 'relevance') === 'pub_date' ? 'pub_date' : 'relevance';
  $from = ymd_ok($a['date_from'] ?? null); $to = ymd_ok($a['date_to'] ?? null);
  if ($from || $to) { $q['mindate'] = $from ?: '1900'; $q['maxdate'] = $to ?: '3000'; $q['datetype'] = in_array($a['datetype'] ?? '', ['edat', 'pdat', 'mdat'], true) ? $a['datetype'] : 'pdat'; }
  $j = json_decode(ncbi('esearch.fcgi', $q, $ttl), true)['esearchresult'] ?? null;
  if (!$j) throw new RuntimeException('pubmed_unavailable');
  return ['pmids' => array_values($j['idlist'] ?? []), 'total_count' => (int)($j['count'] ?? 0)];
}
function pm_meta(array $pmids, int $ttl = 86400): array {
  $ids = array_values(array_filter(array_map('strval', $pmids), fn($x) => preg_match('/^\d{1,9}$/', $x)));
  $ids = array_slice($ids, 0, 20); if (!$ids) return ['articles' => []];
  $xml = @simplexml_load_string(ncbi('efetch.fcgi', ['id' => implode(',', $ids), 'retmode' => 'xml'], $ttl));
  if (!$xml) throw new RuntimeException('pubmed_unavailable');
  $arts = [];
  foreach ($xml->PubmedArticle as $pa) {
    $mc = $pa->MedlineCitation; $art = $mc->Article; $j = $art->Journal;
    $pd = $j->JournalIssue->PubDate; $ad = $art->ArticleDate;
    $date = ['year' => (string)($pd->Year ?: ($ad->Year ?? '')), 'month' => (string)($pd->Month ?: ($ad->Month ?? '')), 'day' => (string)($pd->Day ?: ($ad->Day ?? ''))];
    if ($date['year'] === '' && $pd->MedlineDate) $date['year'] = substr((string)$pd->MedlineDate, 0, 4);
    $doi = ''; foreach ($pa->PubmedData->ArticleIdList->ArticleId ?? [] as $id) if ((string)$id['IdType'] === 'doi') $doi = (string)$id;
    if ($doi === '') foreach ($art->ELocationID ?? [] as $e) if ((string)$e['EIdType'] === 'doi') $doi = (string)$e;
    $types = []; foreach ($art->PublicationTypeList->PublicationType ?? [] as $t) $types[] = (string)$t;
    $abs = []; foreach ($art->Abstract->AbstractText ?? [] as $t) $abs[] = trim(strip_tags($t->asXML()));
    $arts[] = [
      'title' => trim(strip_tags((string)$art->ArticleTitle->asXML())),
      'journal' => ['iso_abbreviation' => (string)$j->ISOAbbreviation, 'title' => (string)$j->Title],
      'publication_date' => $date, 'doi' => $doi, 'identifiers' => ['pmid' => (string)$mc->PMID, 'doi' => $doi],
      'article_types' => $types, 'abstract' => implode(' ', $abs),
    ];
  }
  return ['articles' => $arts];
}

/* ---------- Today's edition, as text for Claude ---------- */
function edition(): array {
  $ctxf = __DIR__ . '/pulse-context.json';
  $idx = is_file(__DIR__ . '/data/edition.html') ? __DIR__ . '/data/edition.html' : __DIR__ . '/index.html';
  $ver = (string)@filemtime($idx) . '-' . (string)@filemtime($ctxf);
  $c = is_file($ctxf) ? json_decode((string)file_get_contents($ctxf), true) : null;
  if (is_array($c) && !empty($c['edition']) && !empty($c['page']) && @filemtime($ctxf) >= @filemtime($idx) - 120) {
    return ['ver' => $ver, 'edition' => mb_substr($c['edition'], 0, 60000), 'page' => mb_substr($c['page'], 0, 150000)];
  }
  // Fallback: read the visible text of each tab straight from index.html.
  $doc = new DOMDocument(); libxml_use_internal_errors(true);
  $doc->loadHTML('<?xml encoding="utf-8"?>' . (string)@file_get_contents($idx)); libxml_clear_errors();
  foreach (iterator_to_array($doc->getElementsByTagName('script')) as $s) $s->parentNode->removeChild($s);
  foreach (iterator_to_array($doc->getElementsByTagName('style')) as $s) $s->parentNode->removeChild($s);
  $clean = fn($t) => preg_replace("/\n\s*\n+/", "\n", preg_replace('/[ \t]+/', ' ', $t));
  $ed = []; foreach (['p-daily', 'p-overview', 'p-biocat', 'p-pharma', 'p-ag', 'p-synbio', 'p-policy'] as $id) { $n = $doc->getElementById($id); if ($n) $ed[] = $n->textContent; }
  $pg = []; $xp = new DOMXPath($doc);
  foreach ($xp->query('//header[contains(@class,"masthead")]') as $h) $pg[] = 'EDITION: ' . $h->textContent;
  foreach ($xp->query('//*[contains(concat(" ",@class," ")," tabpanel ")]') as $p) $pg[] = "\n=== TAB: " . $p->getAttribute('id') . " ===\n" . $p->textContent;
  return ['ver' => $ver, 'edition' => mb_substr($clean(implode("\n", $ed)), 0, 60000), 'page' => mb_substr($clean(implode("\n", $pg)), 0, 150000)];
}

/* ---------- Claude ---------- */
function claude(string $model, string $system, array $messages, int $maxTokens, array $tools = []): array {
  global $C;
  $req = ['model' => $model, 'max_tokens' => $maxTokens,
    'system' => [['type' => 'text', 'text' => $system, 'cache_control' => ['type' => 'ephemeral', 'ttl' => '1h']]],
    'messages' => $messages];
  if ($tools) $req['tools'] = $tools;
  [$code, $body] = http($C['ANTHROPIC_URL'], json_encode($req, JSON_UNESCAPED_UNICODE), [
    'content-type: application/json', 'anthropic-version: 2023-06-01', 'x-api-key: ' . trim((string)$C['ANTHROPIC_API_KEY'])], 150);
  $j = json_decode($body, true);
  if ($code !== 200 || !is_array($j)) {
    $t = $j['error']['type'] ?? '';
    error_log('BMP claude error ' . $code . ' ' . substr($body, 0, 300));
    if ($code === 429 || $t === 'rate_limit_error' || $code === 529) throw new RuntimeException('rate_limited');
    if ($code === 401 || $code === 403) throw new RuntimeException('not_configured');
    if ($code === 400 && str_contains($body, 'credit')) throw new RuntimeException('budget_exhausted');
    throw new RuntimeException('upstream_error');
  }
  record_cost($model, $j['usage'] ?? []);
  return $j;
}
function text_of(array $resp): string { $t = ''; foreach ($resp['content'] ?? [] as $b) if (($b['type'] ?? '') === 'text') $t .= $b['text']; return $t; }
function parse_json_obj(string $t): ?array {
  $t = preg_replace('/^```(?:json)?\s*|\s*```$/m', '', trim($t));
  $a = strpos($t, '{'); $b = strrpos($t, '}'); if ($a === false || $b === false) return null;
  $v = json_decode(substr($t, $a, $b - $a + 1), true); return is_array($v) ? $v : null;
}

function deepdive_system(string $edition): string {
  return "You are the research engine for the Deep Dive tab of BioMarket Pulse, a market-intelligence dashboard on biotech, pharma, synthetic biology, biocatalysis and agriculture (global and Brazil). The user's message is a company or sector name.\n"
  . "Decide whether it is a company or a sector. Then return ONLY one JSON object (no prose, no code fences) with this shape:\n"
  . '{"kind":"company"|"sector","name":"canonical name","summary":"2-3 sentences: what it is, where it stands, what matters now","competitors":[{"name":"","hq":"City, Country","segment":"what they do, 4-8 words","status":"Public (TICKER)"|"Private"|"Acquired by X","total_funding_usd_m":number|null,"last_round":{"type":"Seed|Series A|...|IPO|Debt|Grant","amount_usd_m":number|null,"year":number|null},"momentum":0-5,"why":"one sentence: how it competes or compares"}],"news":[{"date":"YYYY-MM or YYYY-MM-DD","headline":"","why":"one short sentence on significance","from_edition":true|false}],"caveat":"one sentence on what may be out of date"}' . "\n"
  . "Rules: For a company, put the company itself FIRST in competitors, then its 8-10 closest competitors. For a sector, list the 10 most important companies (leaders plus notable challengers). total_funding_usd_m = total private capital raised (for public companies, null unless widely reported). momentum = your judgment of recent activity (deals, launches, raises, clinical or commercial progress): 5 very active, 0 dormant or struggling. Use null for any figure you are not confident about; never guess numbers. news: 4-8 highlights, newest first; FIRST use items from TODAY'S EDITION below that mention these companies or this sector (set from_edition true and copy the headline exactly as written there), then add notable older developments you know (from_edition false). Today is " . date('Y-m-d') . "; your own knowledge may end earlier, so say so in caveat. If the input is not a plausible company or sector name in these industries, return {\"kind\":\"sector\",\"name\":\"\",\"summary\":\"Not a company or sector this dashboard covers.\",\"competitors\":[],\"news\":[],\"caveat\":\"\"}.\n\nTODAY'S EDITION:\n" . $edition;
}
function ask_system(string $page): string {
  return "You are the assistant inside BioMarket Pulse, a public daily market-intelligence dashboard on biotech, pharma, synthetic biology, biocatalysis and global & Brazilian agriculture, read by executives and investors in ag-biotech, synthetic biology and pharma. Answer questions about markets, deals and news ONLY from the dashboard content below; if the answer isn't there, say so plainly and suggest what to look up. Politely decline anything unrelated to this dashboard's subjects. When the user asks for papers, literature or research on a subject, call the search_pubmed tool (one or two focused PubMed queries; use field tags like [Title] when useful) and also check the Research Papers lists in the dashboard content. Recommend 3-6 papers: for each give the title, journal, year, one line on why it is worth reading, and its DOI as a markdown link [DOI](https://doi.org/...). Say the papers come from PubMed. Never cite a paper you did not get from the tool or the dashboard. Be concise and concrete: lead with the answer, use short paragraphs or '- ' bullets, cite figures and dates exactly as given, name the source when useful. No headings. Never invent numbers or references. This is not investment advice; say so if asked what to buy or sell.\n\nDASHBOARD CONTENT:\n" . $page;
}
const PUBMED_TOOL = ['name' => 'search_pubmed',
  'description' => 'Search PubMed for papers on a subject. Returns up to 8 papers, each with title, journal, year, publication type, DOI, PMID and the start of the abstract. Use for any request for papers, literature or research.',
  'input_schema' => ['type' => 'object', 'properties' => [
    'query' => ['type' => 'string', 'description' => "PubMed query, e.g. 'artificial metalloenzyme[Title] AND photocatalysis'"],
    'sort' => ['type' => 'string', 'enum' => ['relevance', 'pub_date'], 'description' => 'relevance (default) or newest first'],
    'since_year' => ['type' => 'string', 'description' => 'optional earliest publication year, e.g. 2024']], 'required' => ['query']]];

function run_pubmed_tool(array $in): array {
  try {
    $a = ['query' => (string)($in['query'] ?? ''), 'max_results' => 8, 'sort' => ($in['sort'] ?? '') === 'pub_date' ? 'pub_date' : 'relevance'];
    if (!empty($in['since_year']) && preg_match('/^\d{4}$/', (string)$in['since_year'])) $a['date_from'] = (string)$in['since_year'];
    $s = pm_search($a); if (!$s['pmids']) return ['papers' => [], 'note' => 'No results; try broader terms.'];
    $m = pm_meta(array_slice($s['pmids'], 0, 8));
    return ['papers' => array_map(fn($x) => ['title' => $x['title'], 'journal' => $x['journal']['iso_abbreviation'] ?: $x['journal']['title'],
      'year' => $x['publication_date']['year'], 'type' => implode(', ', array_diff($x['article_types'], ['Journal Article'])),
      'doi' => $x['doi'], 'pmid' => $x['identifiers']['pmid'], 'abstract' => mb_substr($x['abstract'], 0, 350)], $m['articles'])];
  } catch (Throwable $e) { return ['papers' => [], 'note' => 'PubMed search failed; answer from the dashboard lists instead.']; }
}

/* ---------- Brazil biologicals registry: MAPA AGROFIT via Embrapa AgroAPI (free, 100k calls/month) ---------- */
const AGRO_BASE = 'https://api.cnptia.embrapa.br';
function agro_file(): string { return data_dir() . '/br-bio.json'; }
function agro_configured(): bool { global $C; return trim((string)$C['AGROAPI_KEY']) !== '' && trim((string)$C['AGROAPI_SECRET']) !== ''; }
function agro_date(?string $s): ?string { return $s && preg_match('~^(\d{2})/(\d{2})/(\d{4})~', $s, $m) ? "$m[3]-$m[2]-$m[1]" : null; }
function agro_get(string $tok, string $path, array $q = []): array {
  $url = AGRO_BASE . '/agrofit/v1' . $path . ($q ? '?' . http_build_query($q) : '');
  for ($try = 1; $try <= 4; $try++) {
    [$code, $body] = http($url, null, ['Authorization: Bearer ' . $tok, 'Accept: application/json'], 45);
    if ($code === 200) { $j = json_decode($body, true); if (is_array($j)) return $j; }
    if ($code === 401 || $code === 403) throw new RuntimeException('agroapi_auth');
    sleep(2 * $try);
  }
  throw new RuntimeException('agroapi_unavailable');
}
function agro_clean_ai(string $s): string {
  $s = preg_replace('/\s*\(Produto Microbiol[^)]*\)/iu', '', $s);
  $s = preg_replace('/\s*\([\d.,]+\s*[^()]*\)\s*$/u', '', $s);
  return trim($s);
}
/* Pull every biological class from AGROFIT and write one compact snapshot. Returns a short summary. */
function agro_sync(): array {
  global $C;
  if (!agro_configured()) throw new RuntimeException('not_configured');
  $lock = fopen(data_dir() . '/br-bio.lock', 'c');
  if (!$lock || !flock($lock, LOCK_EX | LOCK_NB)) return ['busy' => true];
  @set_time_limit(170);
  touch(data_dir() . '/br-bio.try');
  [$code, $body] = http(AGRO_BASE . '/token', 'grant_type=client_credentials',
    ['Authorization: Basic ' . base64_encode($C['AGROAPI_KEY'] . ':' . $C['AGROAPI_SECRET']), 'Content-Type: application/x-www-form-urlencoded'], 30);
  $tok = (string)(json_decode($body, true)['access_token'] ?? '');
  if ($code !== 200 || $tok === '') throw new RuntimeException('agroapi_auth');
  $classes = array_values(array_filter(array_map(fn($c) => (string)($c['nome'] ?? ''), agro_get($tok, '/classes-categorias-agronomicas')),
    fn($n) => preg_match('/microbiol|biol[óo]gico|fer[oô]m/iu', $n)));
  if (!$classes) throw new RuntimeException('agroapi_unavailable');
  $ver = agro_get($tok, '/versao'); $srcUpdated = (string)($ver[0]['data_ultima_atualizacao'] ?? '');
  $all = [];
  foreach ($classes as $cl) {
    for ($pg = 1; $pg <= 40; $pg++) {
      $d = agro_get($tok, '/search/produtos-formulados', ['classe_categoria_agronomica' => $cl, 'page' => $pg]);
      foreach ($d as $p) if (!empty($p['numero_registro'])) $all[(string)$p['numero_registro']] = $p;
      if (count($d) < 100) break;
      usleep(300000);
    }
  }
  $prev = is_file(agro_file()) ? (json_decode((string)file_get_contents(agro_file()), true) ?: []) : [];
  $prevSeen = []; foreach ($prev['items'] ?? [] as $it) $prevSeen[$it['r']] = $it['s'] ?? null;
  if ($prevSeen && count($all) < 0.7 * count($prevSeen)) throw new RuntimeException('incomplete_pull');
  if (count($all) < 100) throw new RuntimeException('incomplete_pull');
  $today = date('Y-m-d'); $first = !$prevSeen; $new = 0; $items = [];
  foreach ($all as $reg => $p) {
    $dates = []; foreach ($p['documento_cadastrado'] ?? [] as $x) if ($dd = agro_date($x['data_inclusao'] ?? null)) $dates[] = $dd;
    $crops = []; $pests = [];
    foreach ($p['indicacao_uso'] ?? [] as $u) {
      if (!empty($u['cultura'])) $crops[$u['cultura']] = 1;
      $pn = $u['praga_nome_comum'][0] ?? ($u['praga_nome_cientifico'] ?? ''); if ($pn !== '') $pests[$pn] = 1;
    }
    $seen = array_key_exists($reg, $prevSeen) ? $prevSeen[$reg] : ($first ? null : $today);
    if (!$first && !array_key_exists($reg, $prevSeen)) $new++;
    $items[] = ['r' => (string)$reg, 'b' => array_values($p['marca_comercial'] ?? []), 'c' => (string)($p['titular_registro'] ?? ''),
      'k' => (string)($p['classe_categoria_agronomica'][0] ?? ''), 'a' => array_values(array_unique(array_map('agro_clean_ai', $p['ingrediente_ativo'] ?? []))),
      'f' => (string)($p['formulacao'] ?? ''), 't' => (string)($p['classificacao_toxicologica'] ?? ''), 'e' => (string)($p['classificacao_ambiental'] ?? ''),
      'o' => !empty($p['produto_agricultura_organica']), 'u' => array_slice(array_keys($crops), 0, 40), 'z' => array_slice(array_keys($pests), 0, 12),
      'd' => $dates ? min($dates) : null, 's' => $seen, 'l' => (string)($p['url_agrofit'] ?? '')];
  }
  usort($items, fn($a, $b) => strcmp((string)($b['s'] ?? $b['d']), (string)($a['s'] ?? $a['d'])) ?: strcmp($a['r'], $b['r']));
  $snap = ['generated' => gmdate('c'), 'source_updated' => $srcUpdated, 'baseline' => $prev['baseline'] ?? $today, 'count' => count($items), 'items' => $items];
  $tmp = agro_file() . '.tmp';
  file_put_contents($tmp, json_encode($snap, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES));
  rename($tmp, agro_file());
  flock($lock, LOCK_UN);
  return ['ok' => true, 'count' => count($items), 'new_since_last' => $new, 'classes' => $classes];
}

/* ---------- command line: php api.php sync (daily cron) ---------- */
if (PHP_SAPI === 'cli') {
  if (($argv[1] ?? '') === 'sync') {
    try { echo json_encode(agro_sync(), JSON_UNESCAPED_UNICODE) . "\n"; exit(0); }
    catch (Throwable $e) { fwrite(STDERR, 'sync failed: ' . $e->getMessage() . "\n"); exit(1); }
  }
  echo "usage: php api.php sync\n"; exit(2);
}

/* ---------- request ---------- */
if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') fail('post_only', 405);
$host = strtolower(preg_replace('/:\d+$/', '', $_SERVER['HTTP_HOST'] ?? ''));
$orig = $_SERVER['HTTP_ORIGIN'] ?? ($_SERVER['HTTP_REFERER'] ?? '');
if ($orig !== '' && strtolower((string)parse_url($orig, PHP_URL_HOST)) !== $host) fail('forbidden', 403);
if (($_SERVER['HTTP_X_BMP'] ?? '') !== '1') fail('forbidden', 403);
$in = json_decode((string)file_get_contents('php://input', false, null, 0, 200000), true);
if (!is_array($in)) fail('bad_request');
$action = (string)($in['action'] ?? '');

try {
  switch ($action) {
    case 'status':
      $why = claude_open();
      out(['ok' => true, 'pubmed' => true, 'claude' => $why === null, 'reason' => $why]);

    case 'pm_search':
      if (!take('pm', 400)) fail('daily_limit', 429);
      out(['ok' => true, 'payload' => pm_search($in['args'] ?? [])]);

    case 'pm_meta':
      if (!take('pm', 400)) fail('daily_limit', 429);
      out(['ok' => true, 'payload' => pm_meta((array)(($in['args'] ?? [])['pmids'] ?? []))]);

    case 'br_bio':
      $f = agro_file(); $age = is_file($f) ? time() - (int)filemtime($f) : PHP_INT_MAX;
      $tried = is_file(data_dir() . '/br-bio.try') ? time() - (int)filemtime(data_dir() . '/br-bio.try') : PHP_INT_MAX;
      if ($age > 30 * 3600 && $tried > 900 && agro_configured()) { try { agro_sync(); } catch (Throwable $e) { error_log('BMP agro ' . $e->getMessage()); } }
      if (!is_file($f)) fail(agro_configured() ? 'unavailable' : 'not_configured', 503);
      if (!ini_get('zlib.output_compression')) ob_start('ob_gzhandler');
      echo '{"ok":true,"data":' . file_get_contents($f) . '}'; exit;

    case 'deepdive':
      $term = trim(preg_replace('/\s+/', ' ', (string)($in['term'] ?? '')));
      if ($term === '' || mb_strlen($term) > 80) fail('bad_term');
      $ed = edition();
      $ck = 'dd|' . $ed['ver'] . '|' . $C['DEEPDIVE_MODEL'] . '|' . mb_strtolower($term);
      if (($hit = cache_get($ck, (int)$C['DEEPDIVE_CACHE_HOURS'] * 3600)) !== null) out(['ok' => true, 'cached' => true, 'data' => $hit]);
      if ($why = claude_open()) fail($why, 503);
      if (!take('dd', (int)$C['DEEPDIVES_PER_VISITOR_PER_DAY'])) fail('daily_limit', 429);
      if (!hourly_ok()) fail('rate_limited', 429);
      $sys = deepdive_system($ed['edition']);
      $msgs = [['role' => 'user', 'content' => $term]];
      $d = null;
      for ($i = 0; $i < 2 && !$d; $i++) {
        $r = claude($C['DEEPDIVE_MODEL'], $sys, $msgs, 6000);
        $d = parse_json_obj(text_of($r));
        if ($d && !is_array($d['competitors'] ?? null)) $d = null;
      }
      if (!$d) fail('invalid_json', 502);
      cache_put($ck, $d);
      out(['ok' => true, 'cached' => false, 'data' => $d]);

    case 'ask':
      $turns = [];
      foreach (array_slice((array)($in['turns'] ?? []), -12) as $t) {
        $role = ($t['role'] ?? '') === 'assistant' ? 'assistant' : 'user';
        $txt = mb_substr(trim((string)($t['content'] ?? '')), 0, $role === 'user' ? 1500 : 6000);
        if ($txt !== '') $turns[] = ['role' => $role, 'content' => $txt];
      }
      while ($turns && $turns[0]['role'] !== 'user') array_shift($turns);
      if (!$turns || end($turns)['role'] !== 'user') fail('bad_request');
      $ed = edition();
      $single = count($turns) === 1;
      $ck = 'ask|' . $ed['ver'] . '|' . $C['ASK_MODEL'] . '|' . mb_strtolower($turns[0]['content']);
      if ($single && ($hit = cache_get($ck, 6 * 3600)) !== null) out(['ok' => true, 'cached' => true, 'text' => $hit['text'], 'truncated' => false]);
      if ($why = claude_open()) fail($why, 503);
      if (!take('ask', (int)$C['ASKS_PER_VISITOR_PER_DAY'])) fail('daily_limit', 429);
      $sys = ask_system($ed['page']); $msgs = $turns; $text = ''; $stop = '';
      for ($i = 0; $i < 4; $i++) {
        if (!hourly_ok()) fail('rate_limited', 429);
        $r = claude($C['ASK_MODEL'], $sys, $msgs, 1500, [PUBMED_TOOL]);
        $stop = (string)($r['stop_reason'] ?? ''); $text = text_of($r);
        if ($stop !== 'tool_use') break;
        $msgs[] = ['role' => 'assistant', 'content' => $r['content']];
        $res = [];
        foreach ($r['content'] as $b) if (($b['type'] ?? '') === 'tool_use')
          $res[] = ['type' => 'tool_result', 'tool_use_id' => $b['id'], 'content' => json_encode(run_pubmed_tool((array)$b['input']), JSON_UNESCAPED_UNICODE)];
        $msgs[] = ['role' => 'user', 'content' => $res];
      }
      if (trim($text) === '') fail('empty_completion', 502);
      if ($single && $stop === 'end_turn') cache_put($ck, ['text' => $text]);
      out(['ok' => true, 'cached' => false, 'text' => $text, 'truncated' => $stop === 'max_tokens']);

    default: fail('bad_request');
  }
} catch (InvalidArgumentException $e) { fail($e->getMessage());
} catch (RuntimeException $e) { $c = $e->getMessage(); fail($c, in_array($c, ['rate_limited'], true) ? 429 : 503);
} catch (Throwable $e) { error_log('BMP ' . $e); fail('upstream_error', 500); }
