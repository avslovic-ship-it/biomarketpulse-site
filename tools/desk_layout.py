"""Research-desk page template for BioMarket Pulse.

build_site.py calls apply_desk_layout() for every page whose panel id is in
DESKS. The template only rearranges and restyles what the daily edition
already contains (analysis, insights, regulatory snapshot, articles, papers,
audio, tapes, sources); nothing here adds facts, prices or dates.

To switch another desk to this layout, add its panel id to DESKS.
"""
import html, re

# panel id -> desk configuration (identity only; all content comes from the edition)
DESKS = {
    "p-biocat": {
        "kind": "Industrial biology desk",
        "topics": ["Enzyme engineering", "Biomanufacturing", "Artificial enzymes", "Catalytic chemistry"],
        # Watchlist symbols. Prices show when the edition carries them; otherwise the
        # chip is a quote link only (the daily task does not collect these quotes yet).
        "watch": [("CDXS", "Codexis"), ("NSIS-B.CO", "Novonesis"), ("TWST", "Twist Bioscience"), ("DNA", "Ginkgo Bioworks")],
        "watch_tape": None,
    },
    "p-pharma": {
        "kind": "Life sciences desk",
        "topics": ["Deals", "Clinical readouts", "Approvals", "Company and market moves"],
        "watch": [],
        "watch_tape": "bio",  # use the edition's Top biotech tape (HH_TAPES.bio)
    },
    "p-ag": {
        "kind": "Agriculture desk",
        "topics": ["Crop protection", "Seeds and gene editing", "Biologicals", "Brazil harvest and trade"],
        "watch": [],
        "watch_tape": "cm",  # the edition's Commodities tape (HH_TAPES.cm)
    },
    "p-synbio": {
        "kind": "Synthetic biology desk",
        "topics": ["AI protein design", "Biomanufacturing", "Precision fermentation", "Funding"],
        "watch": [("TWST", "Twist Bioscience"), ("DNA", "Ginkgo Bioworks"), ("ABSI", "Absci")],
        "watch_tape": None,
    },
    "p-policy": {
        "kind": "Policy & public health desk",
        "topics": ["Drug pricing and access", "Outbreaks", "Vaccine policy", "Food-chain safety"],
        "watch": [],
        "watch_tape": None,  # no watchlist for this desk
    },
}

# Non-desk pages get the same frame (header, side menu, colours) with their content unchanged.
# slug -> (eyebrow, title, subtitle)
SHELL = {
    "": ("Free market overview", "Market Overview", "Stock moves, sector heatmap, catalyst calendar and today's signals"),
    "daily-pulse": ("Daily briefing", "Daily Pulse", "Five things to know, the lead story and seven days of deal flow"),
    "regulatory": ("Cross-desk tool", "Regulatory Tracker", "FDA, EMA, EPA, EFSA, ANVISA, MAPA and CTNBio decisions, from filing to decision"),
    "deep-dive": ("On-demand analysis", "Deep Dive", "Any company or sector: competitors, funding, activity and the latest news"),
    "about": ("About", "About & methodology", "What BioMarket Pulse covers and how each edition is made"),
    "brazil-crop-protection": ("Agriculture tool · beta", "Brazil Crop Protection", "Search Brazil's MAPA AGROFIT crop-protection registry in English, with a dashboard for every product"),
    "product": ("Brazil registry", "Product dashboard", "Crop-protection product registered in Brazil"),
    "404": ("", "Page not found", ""),
}

# Desk navigation (slug, panel id, label). Order follows the reference design.
DESK_NAV = [
    ("biocatalysis", "p-biocat", "Biocatalysis"),
    ("pharma-biotech", "p-pharma", "Pharma & Biotech"),
    ("agriculture", "p-ag", "Agriculture"),
    ("brazil-crop-protection", "p-brbio", "Brazil Crop Protection"),
    ("synthetic-biology", "p-synbio", "Synthetic Biology"),
    ("policy", "p-policy", "Policy & Public Health"),
    ("regulatory", "p-reg", "Regulatory Tracker"),
]
DISCOVER_NAV = [("deep-dive", "Deep Dive"), ("", "Market Overview"), ("daily-pulse", "Daily Pulse")]
REG_KEY = {"p-biocat": "biocat", "p-pharma": "pharma", "p-ag": "ag", "p-synbio": "synbio", "p-policy": "policy"}

DESK_CSS = r"""<style id="desk-layout">
/* Research desk layout — navy brand strip, teal accents, quiet light surfaces */
body.desk{
  --ink:#172b43; --muted:#566678; --faint:#7d8a96; --line:#dce3e7; --line-strong:#c5d0d6;
  --paper:#eef2f4; --surface:#ffffff; --surface-2:#f5f7f8; --rule:#20354d;
  --accent:#13837e; --accent-ink:#106d69; --accent-tint:#e6f2f0;
  --hl:#13837e; --hl-ink:#106d69; --hl-tint:#e6f2f0;
  --tk-bg:#14273d; --tk2-bg:#14273d; --tk-fg:#dce8ee; --tk-sym:#7fd6cc; --tk-up:#62d6a6; --tk-down:#ff9d90; --tk-sep:#25405c;
  --dk-navy:#172b43; --dk-teal:#13837e; --dk-soft:#e6f2f0;
  background:var(--paper); color:#26384a;
}
body.desk .tape,body.desk .tape.bio{background:var(--tk-bg);border-bottom:2px solid var(--dk-teal);}
body.desk .tape::before,body.desk .tape.bio::before{background:linear-gradient(90deg,var(--tk-bg),transparent);}
body.desk .tape::after,body.desk .tape.bio::after{background:linear-gradient(270deg,var(--tk-bg),transparent);}
body.desk .tape-lbl{background:var(--tk-bg);color:var(--tk-fg);}
body.desk .wrap{max-width:1240px;margin:18px auto 40px;padding:0;background:var(--surface);border:1px solid var(--line);border-radius:12px;}
body.desk a:focus-visible,body.desk button:focus-visible,body.desk summary:focus-visible{outline:2px solid var(--dk-teal);outline-offset:2px;border-radius:3px;}

/* top header */
.dk-top{display:flex;justify-content:space-between;align-items:center;gap:12px 20px;flex-wrap:wrap;padding:14px 24px;border-bottom:1px solid var(--line);}
.dk-brand{font:700 22px/1.1 var(--f-sans);letter-spacing:-.035em;color:#14273d;text-decoration:none;}
.dk-brand span{color:var(--dk-teal);}
.dk-gnav{display:flex;gap:6px 18px;align-items:center;flex-wrap:wrap;font-size:13px;}
.dk-gnav a{color:#516274;text-decoration:none;}
.dk-gnav a:hover{color:var(--dk-navy);text-decoration:underline;}
.dk-gnav a[aria-current]{color:var(--dk-teal);font-weight:600;}
.dk-acct{background:#eaf2f3;color:#34505e;border-radius:5px;padding:6px 10px;font-size:12px;}

/* shell */
.dk-shell{display:grid;grid-template-columns:212px minmax(0,1fr);}
.dk-side{min-width:0;background:var(--surface-2);border-right:1px solid var(--line);padding:18px 12px;}
.dk-side-inner{position:sticky;top:12px;}
.dk-side-t{font:700 10.5px var(--f-sans);text-transform:uppercase;letter-spacing:.13em;color:#7d8a96;margin:4px 9px 8px;}
.dk-side a{display:flex;justify-content:space-between;align-items:center;gap:6px;padding:8px 10px;margin:2px 0;border-radius:6px;color:#506174;text-decoration:none;font-size:13.5px;}
.dk-side a:hover{background:#ebf0f2;color:var(--dk-navy);}
.dk-side a[aria-current="page"]{background:var(--dk-soft);color:#106d69;font-weight:700;}
.dk-side a small{font-size:11.5px;color:#7d8a96;font-weight:500;white-space:nowrap;}
.dk-side a[aria-current="page"] small{color:#106d69;}
.dk-side-rule{height:1px;background:var(--line);margin:14px 8px;}
body.desk main#main{padding:20px 26px 26px;min-width:0;}

/* desk head */
.dk-crumb{font-size:12px;color:#7d8a96;margin-bottom:10px;}
.dk-crumb a{color:#7d8a96;text-decoration:none;} .dk-crumb a:hover{text-decoration:underline;}
.dk-crumb b{color:var(--dk-teal);font-weight:600;}
.dk-head{display:flex;justify-content:space-between;align-items:flex-start;gap:14px;flex-wrap:wrap;margin-bottom:16px;}
.dk-eyebrow{color:var(--dk-teal);font:700 11px var(--f-sans);letter-spacing:.13em;text-transform:uppercase;}
.dk-head h1{font:700 34px/1.08 var(--f-display);letter-spacing:-.02em;margin:6px 0;color:var(--dk-navy);}
.dk-topics{font-size:13.5px;color:var(--muted);margin:0;}
.dk-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;}
.dk-plan{padding:6px 10px;border-radius:5px;background:var(--dk-soft);color:#146c69;font-size:12px;font-weight:600;}

/* desk watchlist */
.dk-watch{display:flex;align-items:stretch;overflow-x:auto;scrollbar-width:thin;border-block:1px solid var(--line);margin:0 0 16px;padding:9px 0;}
.dk-watch .q{flex:0 0 auto;padding:0 14px;border-right:1px solid var(--line);font-size:12px;color:#6b7885;text-decoration:none;min-width:96px;}
.dk-watch .q:last-child{border-right:0;}
.dk-watch .q b{display:block;font-size:13px;color:#26384a;}
.dk-watch a.q:hover b{color:var(--dk-teal);text-decoration:underline;}
.dk-watch .q.lbl{min-width:0;color:#7d8a96;font-size:11px;text-transform:uppercase;letter-spacing:.06em;align-self:center;}
.dk-watch .up{color:#16816e;} .dk-watch .dn{color:#b65b51;}

/* audio (existing player, restyled) */
body.desk .listen-bar{margin:0 0 18px !important;padding:10px 14px !important;border:0 !important;border-radius:6px !important;background:var(--surface-2) !important;}

/* sections */
body.desk .section-head{border-top:2px solid var(--rule);border-bottom:0;padding-top:10px;margin-bottom:8px;display:flex;align-items:baseline;gap:6px 12px;flex-wrap:wrap;}
body.desk .section-head h2{font:700 19px/1.25 var(--f-display);letter-spacing:-.01em;color:var(--dk-navy);margin:0;}
body.desk .section-head .count{font:600 11px var(--f-sans);letter-spacing:.08em;text-transform:uppercase;color:#7b8995;}
body.desk .section-head .desc{font-size:12.5px;color:var(--muted);}
body.desk section{margin-bottom:22px;min-width:0;}
.dk-kicker{display:block;width:100%;order:-1;font:600 11px var(--f-sans);letter-spacing:.08em;text-transform:uppercase;color:#7b8995;}

.dk-analysis{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(260px,.85fr);gap:24px;margin-bottom:6px;}
body.desk .pa-text{font-size:15px;line-height:1.62;color:#3c4e60;margin:0;max-width:none;}
body.desk .pa-ins{display:grid;grid-template-columns:1fr;gap:10px;}
body.desk .pa-ins li{background:transparent;border:0;border-left:3px solid #62aaa2;border-radius:0;padding:3px 0 3px 12px;font-size:13.5px;color:#566678;}
body.desk .pa-ins li::before{content:none;}
body.desk .pa-ins li b{color:#22384c;}

/* regulatory snapshot, grouped by agency */
body.desk .rs .section-head a.rs-go{margin-left:auto;font:600 12px var(--f-sans);letter-spacing:0;text-transform:none;color:var(--dk-teal);}
body.desk .rs-grid{grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:10px;}
body.desk .rs-card{background:var(--surface-2);border:0;border-radius:6px;padding:11px 12px 4px;}
body.desk .rs-card h3{font-size:13.5px;color:#345067;}
body.desk .rs-card li{grid-template-columns:52px 1fr;}
body.desk .rs-card .t{font-size:13px;color:#3c4e60;}

/* articles + papers */
.dk-lower{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(0,.8fr);gap:28px;}
.dk-filters{display:flex;gap:6px;flex-wrap:wrap;margin:2px 0 6px;}
.dk-filters button{font:inherit;font-size:12px;color:#566678;background:transparent;border:1px solid var(--line);padding:4px 10px;border-radius:999px;cursor:pointer;}
.dk-filters button:hover{border-color:#9fb3bd;}
.dk-filters button[aria-pressed="true"]{background:var(--dk-soft);border-color:#b5dbd6;color:#106d69;font-weight:600;}
.dk-filters .n{opacity:.75;margin-left:3px;}
body.desk .item{grid-template-columns:62px 1fr;gap:12px;padding:11px 0;}
body.desk .item .when{font-size:11.5px;}
body.desk .item .headline{font-size:14.5px;color:#24394e;}
body.desk .item .note{font-size:13px;}
body.desk .pp-sec .section-head .desc{flex-basis:100%;}
body.desk .seg button[aria-pressed="true"]{background:var(--dk-navy);color:#fff;border-color:var(--dk-navy);}
body.desk .pp-list li{padding:9px 0;}
body.desk .pp-t{font-size:14px;color:#26384a;}

/* sources + footer */
.dk-sources{border-top:1px solid var(--line);padding-top:10px;margin-top:6px;}
.dk-sources summary{font-size:13px;color:#566678;cursor:pointer;font-weight:600;}
.dk-sources .dk-src-body{font-size:12.5px;color:#6b7885;line-height:1.6;margin-top:8px;}
.dk-sources .dk-src-body p{margin:0 0 8px;}
body.desk footer{border-top:1px solid var(--line);margin:0;padding:12px 26px;font-size:12px;color:#7d8a96;}
body.desk .site-foot{margin:0;padding:12px 26px 18px;}

/* Stock chart popup: momentum trends in a full-width row under the chart, snapshot stays beside it */
body.desk .scm-body{grid-template-columns:minmax(0,1fr) 230px;grid-template-rows:auto 1fr auto auto;row-gap:0;column-gap:18px;}
body.desk .scm-side{display:contents;}
body.desk .scm-chart-wrap{grid-column:1;grid-row:1 / 3;}
body.desk .scm-side>h4:first-of-type{grid-column:2;grid-row:1;}
body.desk #scm-stats{grid-column:2;grid-row:2;align-self:start;}
body.desk .scm-side>h4:last-of-type{grid-column:1 / -1;grid-row:3;margin-top:16px;}
body.desk #scm-trends{grid-column:1 / -1;grid-row:4;display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:10px;}
@media (max-width:760px){
  body.desk .scm-body{grid-template-columns:minmax(0,1fr);grid-template-rows:none;}
  body.desk .scm-chart-wrap,body.desk .scm-side>h4:first-of-type,body.desk .scm-side>h4:last-of-type,body.desk #scm-stats,body.desk #scm-trends{grid-column:1;grid-row:auto;}
  body.desk .scm-side>h4:first-of-type{margin-top:14px;}
}

@media (max-width:900px){
  .dk-shell{grid-template-columns:minmax(0,1fr);}
  .dk-side{border-right:0;border-bottom:1px solid var(--line);padding:6px;}
  .dk-side-inner{position:static;display:flex;gap:4px;overflow-x:auto;scrollbar-width:thin;}
  .dk-side-t,.dk-side-rule{display:none;}
  .dk-side a{white-space:nowrap;flex:0 0 auto;}
  .dk-analysis,.dk-lower{grid-template-columns:1fr;gap:4px;}
}
@media (max-width:620px){
  body.desk .wrap{margin:0;border-radius:0;border-inline:0;}
  .dk-top{padding:12px 16px;}
  body.desk main#main{padding:16px;}
  .dk-head h1{font-size:28px;}
  body.desk footer,body.desk .site-foot{padding-inline:16px;}
  body.desk .item{grid-template-columns:1fr;gap:2px;}
}
</style>
"""

DESK_JS = r"""<script>
/* Research desk: watchlist, article filters, tracker link, tapes */
(function(){
  var cfg=%(cfg)s;
  var esc=function(t){return String(t).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});};
  var yf=function(s){return "https://finance.yahoo.com/quote/"+encodeURIComponent(s.replace(".B","-B"))+"/";};

  /* Site-wide tape stays on Market movers; this desk's own watchlist is shown in the page */
  var mv=document.getElementById("tape-movers"),cm=document.querySelector(".tape.cm"),bio=document.querySelector(".tape.bio");
  function tapes(){if(mv)mv.hidden=false;if(cm)cm.hidden=true;if(bio)bio.hidden=true;}
  if(cfg.desk){tapes(); setTimeout(tapes,0);}

  /* Watchlist */
  var w=document.getElementById("dk-watch");
  if(w){
    var T=window.HH_TAPES||{}, rows=[], asof="";
    if(cfg.watch_tape&&T[cfg.watch_tape]){
      rows=T[cfg.watch_tape].map(function(d){return cfg.watch_tape==="cm"?{s:d[0],p:d[1],c:d[2],u:"https://tradingeconomics.com/commodity/"+d[3]}:{s:d[0],p:d[1],c:d[2]};});
      var lb=document.querySelector("#"+(cfg.watch_tape==="bio"?"bio":cfg.watch_tape==="cm"?"cm":"tape")+"-track .tk.asof .s"); asof=lb?lb.textContent:"";
    } else {
      var all={}; Object.keys(T).forEach(function(k){(T[k]||[]).forEach(function(d){if(typeof d[1]==="number"&&!all[d[0]])all[d[0]]=d;});});
      rows=cfg.watch.map(function(x){var d=all[x[0]];return {s:x[0],n:x[1],p:d?d[1]:null,c:d?d[2]:null};});
      if(rows.some(function(r){return r.p!=null;})){var lb2=document.querySelector("#tape-track .tk.asof .s");asof=lb2?lb2.textContent:"";}
    }
    var h=asof?'<span class="q lbl">'+esc(asof)+'</span>':'<span class="q lbl">Watchlist · quote links</span>';
    h+=rows.map(function(r){
      var body=r.p!=null?'<span class="'+(r.c>=0?'up':'dn')+'">'+(r.c>=0?'+':'−')+Math.abs(r.c).toFixed(1)+'%%</span> · 7D'
                        :esc(r.n||"")+' · quote ↗';
      return '<a class="q" href="'+(r.u||yf(r.s))+'" target="_blank" rel="noopener" title="'+esc(r.s)+(r.u?' on Trading Economics':' on Yahoo Finance')+'"><b>'+esc(r.s)+'</b>'+body+'</a>';
    }).join("");
    h+='<span class="q lbl">'+rows.length+(cfg.watch_tape==="cm"?' markets':' names')+'</span>';
    w.innerHTML=h;
  }

  /* Article type filters */
  var fb=document.querySelector(".dk-filters");
  if(fb){
    var items=[].slice.call(fb.parentNode.querySelectorAll(".items .item"));
    fb.addEventListener("click",function(e){
      var b=e.target.closest("button"); if(!b) return;
      [].forEach.call(fb.querySelectorAll("button"),function(x){x.setAttribute("aria-pressed",x===b?"true":"false");});
      var v=b.dataset.f, n=0;
      items.forEach(function(it){var t=it.querySelector(".tag"),ok=!v||(t&&t.textContent.trim()===v);it.hidden=!ok;if(ok)n++;});
      var st=document.getElementById("dk-filter-status"); if(st) st.textContent=n+" article"+(n===1?"":"s")+" shown";
    });
  }

  /* Regulatory snapshot: link into the full tracker page, filtered to this desk */
  var rs=document.querySelector(".rs[data-reg]");
  if(rs){
    var head=rs.querySelector(".section-head");
    if(head&&cfg.desk){
      var old=head.querySelector(".rs-go"), a=document.createElement("a");
      a.className="rs-go"; a.href=cfg.tracker; a.textContent="Open full tracker →";
      if(old) old.replaceWith(a); else head.appendChild(a);
      var c=head.querySelector(".count"); if(c&&!head.querySelector(".dk-kicker")){var k=document.createElement("span");k.className="dk-kicker";k.textContent="Cross-agency watch";head.insertBefore(k,head.firstChild);}
    }
  }
  var pl=document.querySelector(".pp-list"); if(pl) pl.setAttribute("aria-live","polite");
})();
</script>
"""

# Regulatory Tracker page: honour ?sector= from a desk's "Open full tracker" link
TRACKER_JS = """<script>
(function(){var m=/[?&]sector=([a-z]+)/.exec(location.search);if(!m)return;
var b=document.querySelector('.rt-seg[data-f="sector"] button[data-v="'+m[1]+'"]');if(b)b.click();})();
</script>
"""


def _href(slug, preview):
    if preview:
        return (slug or "overview") + ".html"
    return "/" + (slug + "/" if slug else "")


def _cut(s, pattern, flags=re.S):
    m = re.search(pattern, s, flags)
    if not m:
        return s, ""
    return s[:m.start()] + s[m.end():], m.group(0)


def _top_sections(panel):
    """Split a tab panel body into its top-level <section> blocks, in order."""
    out, i = [], 0
    while True:
        m = re.compile(r"<section\b").search(panel, i)
        if not m:
            break
        depth, j = 0, m.start()
        for t in re.finditer(r"<(/?)section\b[^>]*>", panel[m.start():]):
            depth += -1 if t.group(1) else 1
            if depth == 0:
                j = m.start() + t.end()
                break
        out.append(panel[m.start():j])
        i = j
    return out


def _filters(articles):
    labels = re.findall(r'<span class="tag [a-z]+">([^<]+)</span>', articles)
    if len(set(labels)) < 2:
        return articles
    order, count = [], {}
    for l in labels:
        if l not in count:
            order.append(l)
        count[l] = count.get(l, 0) + 1
    order.sort(key=lambda l: -count[l])
    btn = [f'<button type="button" aria-pressed="true" data-f="">All<span class="n">{len(labels)}</span></button>']
    for l in order:
        raw = html.unescape(l)
        btn.append(f'<button type="button" aria-pressed="false" data-f="{html.escape(raw)}">{l}<span class="n">{count[l]}</span></button>')
    bar = ('<div class="dk-filters" role="group" aria-label="Filter articles by type">' + "".join(btn) +
           '</div><span class="sr-only" id="dk-filter-status" aria-live="polite" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)"></span>')
    return articles.replace('<div class="items">', bar + '\n      <div class="items">', 1)


def _analysis(pa):
    h2 = re.search(r"<h2>(.*?)</h2>", pa, re.S)
    cnt = re.search(r'<span class="count">(.*?)</span>', pa, re.S)
    txt = re.search(r'<p class="pa-text">.*?</p>', pa, re.S)
    ins_h = re.search(r'<h3 class="pa-h">(.*?)</h3>', pa, re.S)
    ins = re.search(r'<ol class="pa-ins">.*?</ol>', pa, re.S)
    if not (h2 and txt and ins):
        return pa  # unexpected shape: keep the module as it is
    kicker = "Market synthesis" + (" · " + cnt.group(1) if cnt else "")
    return (
        '<div class="dk-analysis">\n'
        '  <section class="pa" aria-labelledby="dk-pa-h"><div class="section-head">'
        f'<span class="dk-kicker">{kicker}</span><h2 id="dk-pa-h">{h2.group(1)}</h2></div>\n    {txt.group(0)}\n  </section>\n'
        '  <section class="dk-ins" aria-labelledby="dk-ins-h"><div class="section-head">'
        f'<span class="dk-kicker">Editor’s read-through</span><h2 id="dk-ins-h">{ins_h.group(1) if ins_h else "Three actionable insights"}</h2></div>\n    {ins.group(0)}\n  </section>\n'
        '</div>\n')


def apply_layout(doc, pid, slug, label, counts, date_label, edition_no, preview):
    """Research-desk look for one built page: a full desk for panels in DESKS,
    the shared frame (header, side menu, colours) for every other page."""
    import json
    is_desk = pid in DESKS
    cfg = DESKS.get(pid)
    shell = SHELL.get(slug)
    if not is_desk and shell is None:
        return doc
    cur_slug = None if is_desk else slug
    doc = re.sub(r"<body(?![^>]*class=)", '<body class="desk"', doc, count=1)
    # audio player is moved into the page body, not duplicated
    doc, listen = _cut(doc, r'\s*<section class="listen-bar".*?</section>')
    # masthead + section tabs -> brand bar with site navigation
    gnav = [("", "Market Overview"), ("daily-pulse", "Daily Pulse"), ("biocatalysis", "Research desks"),
            ("regulatory", "Regulatory Tracker"), ("about", "About")]
    def is_cur(s):
        return (s == "biocatalysis" and is_desk) or (not is_desk and s == slug)
    links = "".join(
        f'<a href="{_href(s, preview)}"{" aria-current=\"true\"" if is_cur(s) else ""}>{html.escape(l)}</a>'
        for s, l in gnav)
    top = (f'<header class="dk-top"><a class="dk-brand" href="{_href("", preview)}">BioMarket <span>Pulse</span></a>'
           f'<nav class="dk-gnav" aria-label="Site">{links}' + ('<span class="dk-acct">Sandbox preview · accounts not connected</span>' if preview else "") + '</nav></header>\n')
    doc = re.sub(r'<header class="masthead">.*?</header>', lambda m: top, doc, count=1, flags=re.S)
    doc = re.sub(r'\s*<nav class="tabs" id="tabs".*?</nav>\s*<script>\(function\(\)\{var c=document\.querySelector\(\'\.tabs.*?</script>',
                 "", doc, count=1, flags=re.S)
    doc, src = _cut(doc, r'\s*<div class="sources">.*?</div>(?=\s*<div>)')
    m = re.search(r'<main id="main">(.*?)</main>', doc, re.S)
    if not m:
        return doc
    panel = m.group(1)

    side = ['<aside class="dk-side" aria-label="Research desks"><div class="dk-side-inner">',
            '<div class="dk-side-t">Research desks</div>']
    for dslug, dpid, dl in DESK_NAV:
        n = counts.get(dpid)
        cur = ' aria-current="page"' if (dpid == pid or dslug == cur_slug) else ""
        side.append(f'<a href="{_href(dslug, preview)}"{cur}>{html.escape(dl)}{f"<small>{n} items</small>" if n else ""}</a>')
    side.append('<div class="dk-side-rule"></div><div class="dk-side-t">Discover</div>')
    for dslug, dl in DISCOVER_NAV:
        cur = ' aria-current="page"' if dslug == cur_slug else ""
        side.append(f'<a href="{_href(dslug, preview)}"{cur}>{html.escape(dl)}</a>')
    side.append("</div></aside>")

    if is_desk:
        kind, title, sub = cfg["kind"], label, " · ".join(html.escape(t) for t in cfg["topics"])
    else:
        kind, title, sub = shell[0], shell[1], html.escape(shell[2])
    eyebrow = " · ".join(x for x in (kind, f"Edition No. {edition_no}" if edition_no else "", date_label) if x)
    crumb_mid = "Research desks&nbsp; / &nbsp;" if is_desk else ""
    head = (f'<nav class="dk-crumb" aria-label="Breadcrumb"><a href="{_href("", preview)}">BioMarket Pulse</a>&nbsp; / &nbsp;{crumb_mid}<b>{html.escape(title)}</b></nav>\n'
            f'<div class="dk-head"><div><div class="dk-eyebrow">{html.escape(eyebrow)}</div><h1>{html.escape(title)}</h1>'
            + (f'<p class="dk-topics">{sub}</p>' if sub else "") + '</div>'
            + ('<div class="dk-actions"><span class="dk-plan">Free during preview</span></div>' if (is_desk and preview) else "") + '</div>\n')
    if is_desk and (cfg["watch"] or cfg["watch_tape"]):
        head += f'<div class="dk-watch" id="dk-watch" aria-label="{html.escape(label)} watchlist"></div>\n'

    sources = ""
    if src:
        body = re.sub(r'^\s*<div class="sources">|</div>\s*$', "", src.strip())
        sources = ('<details class="dk-sources"><summary>Sources &amp; methodology · refreshed with each edition</summary>'
                   f'<div class="dk-src-body"><p>{body}</p>'
                   f'<p>Compiled each morning as part of edition No. {edition_no}. Every article, regulatory action and paper links to its original source. '
                   f'See <a href="{_href("about", preview)}">About &amp; methodology</a>.</p></div></details>\n')

    if is_desk:
        secs = _top_sections(panel)
        pa = next((s for s in secs if s.startswith('<section class="pa"')), "")
        rs = next((s for s in secs if 'class="rs"' in s[:40]), "")
        pp = next((s for s in secs if s.startswith('<section class="pp-sec"')), "")
        arts = next((s for s in secs if "<h2>Latest Articles</h2>" in s), "")
        ai = secs.index(arts) if arts else len(secs)
        early = [s for i, s in enumerate(secs) if s not in (pa, rs, pp, arts) and i < ai]  # e.g. Brazil registry search
        late = [s for i, s in enumerate(secs) if s not in (pa, rs, pp, arts) and i > ai]
        loose = panel
        for s_ in secs:
            loose = loose.replace(s_, "")
        loose = re.sub(r'</?div class="tabpanel"[^>]*>|</div>\s*<!-- /p-[a-z]+ -->|<!--.*?-->', "", loose, flags=re.S).strip()
        if loose.strip("</div>\n "):
            print(f"desk_layout: warning — {pid} has content outside its sections; kept below the desk modules")
        content = (_analysis(pa) + rs + "\n" + "\n".join(early) +
                   '<div class="dk-lower">\n' + _filters(arts) + "\n" + pp + "\n</div>\n" + "\n".join(late))
    else:
        content = panel
    new_main = ('\n' + "".join(side) + '\n<main id="main">\n' + head + listen.strip() + "\n" + content + sources + "</main>\n")
    doc = doc[:m.start()] + '<div class="dk-shell">' + new_main + "</div>" + doc[m.end():]

    js_cfg = {"watch": cfg["watch"] if is_desk else [], "watch_tape": cfg["watch_tape"] if is_desk else None,
              "desk": is_desk, "tracker": _href("regulatory", preview) + "?sector=" + REG_KEY.get(pid, "")}
    doc = doc.replace("</head>", DESK_CSS + "</head>", 1)
    doc = doc.replace("</body>", DESK_JS % {"cfg": json.dumps(js_cfg)} + "</body>", 1)
    return doc


def apply_tracker_link(doc):
    return doc.replace("</body>", TRACKER_JS + "</body>", 1)


apply_desk_layout = apply_layout  # backwards name
