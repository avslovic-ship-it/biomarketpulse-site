#!/usr/bin/env python3
"""Build biomarketpulse.com from the single-page daily edition.

    python3 tools/build_site.py EDITION.html [OUT_DIR] [--preview]

EDITION.html is the page the daily task publishes (all tabs in one file).
OUT_DIR defaults to the repo root (the folder above tools/). The build writes one
page per tab, each at its own address (/, /daily-pulse/, /pharma-biotech/ ...), plus
/about/, 404.html, sitemap.xml, robots.txt and data/edition.html (the full edition,
which api.php reads for Deep Dive and Ask the Pulse).

--preview writes flat files (pharma-biotech.html ...) with relative links, for
viewing without a web server.
"""
import datetime, html, json, os, re, sys

SITE = "https://www.biomarketpulse.com"
NAME = "BioMarket Pulse"

# slug, panel id, nav label, page <title>, meta description
PAGES = [
    ("", "p-overview", "Market Overview",
     "BioMarket Pulse — Daily market intelligence for biotech, pharma, synbio and agriculture",
     "Daily market intelligence on biotech, pharma, synthetic biology, biocatalysis and agriculture: deals, launches, regulatory decisions, stock moves and the catalyst calendar."),
    ("daily-pulse", "p-daily", "Daily Pulse",
     "Daily Pulse — Five things to know and deal flow | BioMarket Pulse",
     "The five things that matter today across biotech, pharma, synbio and agriculture, the lead story, and every M&A, licensing, funding and IPO deal of the last seven days."),
    ("biocatalysis", "p-biocat", "Biocatalysis",
     "Biocatalysis — Enzyme engineering news and analysis | BioMarket Pulse",
     "Daily news, analysis, regulatory actions and new research on enzyme engineering, enzyme design and biocatalytic manufacturing."),
    ("pharma-biotech", "p-pharma", "Pharma & Biotech",
     "Pharma & Biotech — Deals, approvals and readouts | BioMarket Pulse",
     "Pharma and biotech M&A, licensing, FDA and EMA decisions, clinical readouts and financings, with daily analysis and new research papers."),
    ("agriculture", "p-ag", "Agriculture",
     "Agriculture — Global and Brazil ag-biotech intelligence | BioMarket Pulse",
     "Crop protection, seeds, biologicals, gene editing and fertilizer news, Brazil harvest and export data, and ag regulatory decisions from EPA, the EU, MAPA and CTNBio."),
    ("synthetic-biology", "p-synbio", "Synthetic Biology",
     "Synthetic Biology — Biomanufacturing and protein design | BioMarket Pulse",
     "AI protein design, biomanufacturing, precision fermentation and synbio funding, with daily analysis, regulatory actions and new research."),
    ("policy", "p-policy", "Policy & Public Health",
     "Policy & Public Health — Drug pricing, outbreaks and food safety | BioMarket Pulse",
     "Drug pricing and market-access policy, outbreaks and WHO actions, vaccine policy, antimicrobial resistance and food-chain safety rules in the US, EU, UK and Brazil."),
    ("regulatory", "p-reg", "Regulatory Tracker",
     "Regulatory Tracker — FDA, EMA, EPA, EFSA and ANVISA decisions | BioMarket Pulse",
     "Track upcoming FDA, EMA, EPA, EFSA, ANVISA and CTNBio decisions for drugs, crop-protection products, food enzymes and GM microbes, from filing to final decision."),
    ("deep-dive", "p-deep", "Deep Dive",
     "Deep Dive — Company and sector analysis | BioMarket Pulse",
     "Type any biotech, pharma, synbio or ag company or sector for its competitors, funding and activity heat map, and the latest news."),
]
ABOUT = ("about", "About BioMarket Pulse",
         "What BioMarket Pulse covers, how each daily edition is compiled, and how to use it.")

PILL_KEYS = {"p-biocat", "p-pharma", "p-ag", "p-synbio", "p-policy"}


def fail(msg):
    sys.exit("build_site: " + msg)


# ---------------------------------------------------------------- site bridge
# Off claude.ai, Deep Dive, Ask the Pulse and the live PubMed lists run through
# /api.php. These edits are applied to every edition; a missing anchor is reported
# and skipped, so a changed page never breaks the build.
BRIDGE_JS = r"""<script>
/* ---- Site bridge: off claude.ai, Deep Dive, Ask and live PubMed run through this site's api.php ---- */
(function(){
  var inClaude=!!(window.claude&&window.claude.use);
  var API=(document.querySelector('meta[name="bmp-api"]')||{}).content||"/api.php";
  function api(action,data,signal){
    return fetch(API,{method:"POST",headers:{"Content-Type":"application/json","X-BMP":"1"},body:JSON.stringify(Object.assign({action:action},data||{})),signal:signal,credentials:"same-origin"})
      .then(function(r){return r.json().catch(function(){return {ok:false,error:"upstream_error"};});},function(e){throw {code:e&&e.name==="AbortError"?"cancelled":"upstream_error"};})
      .then(function(j){if(!j||!j.ok) throw {code:(j&&j.error)||"upstream_error"}; return j;});
  }
  var statusP=null;
  window.BMP={
    on:!inClaude,
    api:api,
    status:function(){ if(!statusP) statusP=api("status").catch(function(){return {ok:false,claude:false,pubmed:false};}); return statusP; },
    mcp:{callTool:function(server,tool,args,opt){
      var a=tool==="search_articles"?"pm_search":tool==="get_article_metadata"?"pm_meta":null;
      if(!a) return Promise.reject({code:"not_in_manifest"});
      return api(a,{args:args},opt&&opt.signal).then(function(j){return {payload:j.payload};});
    }}
  };
})();
</script>
"""

BR_SECTION = r"""<section class="brb" id="br-bio" aria-labelledby="brb-h">
<style>
.brb{margin-top:6px}
.brb .brb-sub{font-size:13.5px;color:var(--muted);margin:10px 0 12px;line-height:1.5}
.brb .brb-box{display:flex;gap:8px;margin:0 0 8px}
.brb .brb-box input{flex:1 1 auto;min-width:0;font:inherit;font-size:17px;padding:12px 14px;border:2px solid var(--hl);background:#fff;color:var(--ink);border-radius:4px}
.brb .brb-box input:focus-visible{outline:3px solid var(--hl-tint);outline-offset:1px}
.brb .brb-ex{font-size:12.5px;color:var(--muted);margin:0 0 10px;display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.brb .brb-chip{border:1px solid var(--line-strong);background:#fff;color:var(--ink);font:inherit;font-size:12.5px;padding:3px 10px;border-radius:999px;cursor:pointer}
.brb .brb-n{font-size:13px;color:var(--muted);margin:4px 0 6px}
.brb .brb-n b{color:var(--ink)}
.brb .brb-list{list-style:none;margin:0;padding:0;border-top:1px solid var(--line)}
.brb .brb-it{padding:11px 2px;border-bottom:1px solid var(--line)}
.brb .brb-l1{display:flex;flex-wrap:wrap;gap:6px 10px;align-items:baseline}
.brb .brb-name{font-weight:700;color:var(--ink);font-size:15px}
.brb .brb-k{font-size:11px;padding:1px 7px;border-radius:3px;color:var(--hl-ink);background:var(--hl-tint)}
.brb .brb-new{font-size:11px;font-weight:700;padding:1px 7px;border-radius:3px;color:#fff;background:var(--accent-ink,#a94300)}
.brb .brb-co{font-size:13px;color:var(--muted);margin-top:2px}
.brb .brb-ai{font-size:13.5px;margin-top:4px;color:var(--ink)}
.brb .brb-meta{font-size:12.5px;color:var(--muted);margin-top:3px;line-height:1.45}
.brb .brb-meta a{white-space:nowrap}
.brb .brb-more{display:block;margin:12px auto 0;font:inherit;font-size:14px;padding:8px 18px;border:1px solid var(--line-strong);background:#fff;color:var(--ink);border-radius:3px;cursor:pointer}
.brb .brb-note{font-size:12px;color:var(--muted);margin-top:12px;line-height:1.5}
.brb .brb-msg{padding:14px 2px;color:var(--muted);font-size:14px}
</style>
  <div class="section-head">
    <h2 id="brb-h">Brazil Biologicals Search</h2>
    <span class="count" id="brb-count">MAPA · AGROFIT</span>
  </div>
  <p class="brb-sub">Type what you're looking for, in English or Portuguese, and get every biological product registered in Brazil that matches. Combine a product type, a crop, a pest or a company.</p>
  <div id="brb-body"><div class="brb-msg">Loading the registry…</div></div>
<script>
(function(){
  var body=document.getElementById("brb-body"); if(!body) return;
  var DATA=null, shown=20, refs={};
  function el(t,c,x){var e=document.createElement(t); if(c) e.className=c; if(x!=null) e.textContent=x; return e;}
  function norm(s){return String(s||"").toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g,"");}
  /* English terms -> the Portuguese words used in AGROFIT. Anything not listed is searched as typed. */
  var SYN={insecticide:["inseticida"],fungicide:["fungicida"],nematicide:["nematicida"],acaricide:["acaricida"],miticide:["acaricida"],bactericide:["bactericida"],
    bioinsecticide:["inseticida"],biofungicide:["fungicida"],bionematicide:["nematicida"],pheromone:["feromonio"],"biological control":["agente biologico"],
    soy:["soja"],soybean:["soja"],corn:["milho"],maize:["milho"],cotton:["algodao"],sugarcane:["cana"],"sugar cane":["cana"],coffee:["cafe"],wheat:["trigo"],rice:["arroz"],
    bean:["feijao"],tomato:["tomate"],potato:["batata"],citrus:["citros","laranja"],orange:["laranja"],banana:["banana"],grape:["uva"],apple:["maca"],eucalyptus:["eucalipto"],
    pasture:["pastagem"],vegetable:["hortalica","olericola"],fruit:["fruta"],sorghum:["sorgo"],peanut:["amendoim"],onion:["cebola"],cassava:["mandioca"],mango:["manga"],
    papaya:["mamao"],strawberry:["morango"],cocoa:["cacau"],tobacco:["fumo"],barley:["cevada"],
    whitefly:["mosca-branca"],caterpillar:["lagarta"],armyworm:["spodoptera","lagarta"],"fall armyworm":["spodoptera"],looper:["lagarta"],mite:["acaro"],aphid:["pulgao"],
    nematode:["nematoide"],"stink bug":["percevejo"],borer:["broca"],"white mold":["mofo-branco"],rust:["ferrugem"],fusarium:["fusari"],thrips:["tripes"],
    leafhopper:["cigarrinha"],weevil:["bicudo","gorgulho"],"root rot":["podridao"],blight:["requeima","queima"],"powdery mildew":["oidio"],"downy mildew":["mildio"]};
  var CROPS={soja:1,milho:1,algodao:1,cana:1,cafe:1,trigo:1,arroz:1,feijao:1,tomate:1,batata:1,citros:1,laranja:1,banana:1,uva:1,maca:1,eucalipto:1,pastagem:1,sorgo:1,amendoim:1,cebola:1,mandioca:1,manga:1,mamao:1,morango:1,cacau:1,fumo:1,cevada:1,hortalica:1,olericola:1,fruta:1};
  var STOP={and:1,or:1,for:1,with:1,in:1,on:1,the:1,of:1,to:1,a:1,e:1,ou:1,de:1,da:1,do:1,para:1,em:1,com:1,"&":1,"+":1,products:1,product:1,produtos:1,produto:1,biological:1,biologicals:1};
  function alts(tok){
    if(SYN[tok]) return SYN[tok];
    var s=tok.replace(/(ies)$/,"y").replace(/(es|s)$/,""); if(SYN[s]) return SYN[s];
    if(SYN[tok.replace(/s$/,"")]) return SYN[tok.replace(/s$/,"")];
    return [tok];
  }
  function parse(q){
    var t=norm(q).replace(/[,;]+/g," ").replace(/\s+/g," ").trim(), out=[], flags={organic:false};
    Object.keys(SYN).filter(function(k){return k.indexOf(" ")>0;}).sort(function(a,b){return b.length-a.length;}).forEach(function(k){
      if(t.indexOf(k)>=0){ out.push({label:k,alts:SYN[k]}); t=t.replace(k," "); }});
    t.split(" ").forEach(function(w){ if(!w||STOP[w]) return; if(w==="organic"||w==="organico"){flags.organic=true; return;} out.push({label:w,alts:alts(w)}); });
    return {terms:out,flags:flags};
  }
  function matches(it,P){
    if(P.flags.organic&&!it.o) return false;
    for(var i=0;i<P.terms.length;i++){
      var ok=false, a=P.terms[i].alts;
      for(var j=0;j<a.length&&!ok;j++){
        if(it._t.indexOf(a[j])>=0) ok=true;
        else if(CROPS[a[j]]&&it._all) ok=true;
      }
      if(!ok) return false;
    }
    return true;
  }
  function load(){
    if(!window.BMP||!window.BMP.on){ fail("The search is available on biomarketpulse.com."); return; }
    window.BMP.api("br_bio").then(function(j){ DATA=j.data; DATA.items.forEach(function(it){
        it._t=norm([it.b.join(" "),it.c,it.r,it.k,it.a.join(" "),it.u.join(" "),it.z.join(" ")].join(" | "));
        it._all=it.u.some(function(c){return /todas as culturas/i.test(c);}); }); build(); run(); },
      function(e){ fail(e&&e.code==="not_configured"?"The search isn't switched on yet.":"The search is temporarily unavailable. Please try again shortly."); });
  }
  function fail(m){body.innerHTML=""; body.appendChild(el("div","brb-msg",m));}
  function build(){
    body.innerHTML="";
    var box=el("div","brb-box"), q=el("input"); q.type="search"; q.id="brb-q"; q.autocomplete="off"; q.placeholder="e.g. insecticide and soy";
    q.setAttribute("aria-label","Search Brazil's registered biologicals");
    q.oninput=function(){shown=20; run();}; box.appendChild(q); body.appendChild(box); refs.q=q;
    var ex=el("div","brb-ex"); ex.appendChild(el("span",null,"Try:"));
    ["insecticide and soy","fungicide corn","nematicide coffee","bacillus","pheromone","Koppert","white mold","organic fungicide"].forEach(function(s){
      var b=el("button","brb-chip",s); b.type="button"; b.onclick=function(){q.value=s; shown=20; run(); q.focus();}; ex.appendChild(b);});
    body.appendChild(ex);
    refs.n=el("div","brb-n"); refs.n.setAttribute("aria-live","polite"); body.appendChild(refs.n);
    refs.list=el("ol","brb-list"); body.appendChild(refs.list);
    refs.more=el("button","brb-more","Show more"); refs.more.type="button"; refs.more.onclick=function(){shown+=40; run();}; body.appendChild(refs.more);
    body.appendChild(el("p","brb-note","Source: MAPA's AGROFIT registry, via Embrapa AgroAPI. MAPA last updated the source data on "+(DATA.source_updated||"an unknown date")+"; this page re-reads it daily and marks a product New when it first appears. Covers formulated biological products (microbial and biological-control agents, pheromones); inoculants and biofertilizers are not included. A product registered for all crops appears in every crop search. Always confirm a registration on the official AGROFIT page before acting on it."));
    document.getElementById("brb-count").textContent=DATA.items.length+" products · MAPA AGROFIT";
  }
  function run(){
    var P=parse(refs.q.value), has=P.terms.length||P.flags.organic;
    var rows=has?DATA.items.filter(function(it){return matches(it,P);}):DATA.items;
    var desc=P.terms.map(function(t){return t.alts[0]===t.label?t.label:t.label+" → "+t.alts.join(" / ");}).concat(P.flags.organic?["organic"]:[]).join("  +  ");
    refs.n.textContent="";
    var b=el("b",null,rows.length+" product"+(rows.length===1?"":"s")); refs.n.appendChild(b);
    refs.n.appendChild(document.createTextNode(has?" matching  "+desc:" in the registry. Type above to narrow them down."));
    refs.list.innerHTML="";
    rows.slice(0,shown).forEach(function(it){
      var li=el("li","brb-it"), l1=el("div","brb-l1");
      l1.appendChild(el("span","brb-name",it.b.length?it.b.join(" · "):"Registration "+it.r));
      l1.appendChild(el("span","brb-k",it.k)); if(it.s) l1.appendChild(el("span","brb-new","New"));
      li.appendChild(l1); li.appendChild(el("div","brb-co",it.c+" · Reg. "+it.r));
      if(it.a.length) li.appendChild(el("div","brb-ai",it.a.join("; ")));
      var m=el("div","brb-meta"), parts=[];
      if(it.u.length) parts.push("Crops: "+it.u.slice(0,5).join(", ")+(it.u.length>5?" +"+(it.u.length-5)+" more":""));
      if(it.z.length) parts.push("Targets: "+it.z.slice(0,5).join(", ")+(it.z.length>5?" …":""));
      if(it.o) parts.push("Approved for organic farming");
      if(it.d) parts.push("First filed "+it.d.slice(0,7));
      m.textContent=parts.join(" · ")+(parts.length?" · ":"");
      if(it.l){var a=el("a",null,"AGROFIT ↗"); a.href=it.l; a.target="_blank"; a.rel="noopener"; m.appendChild(a);}
      li.appendChild(m); refs.list.appendChild(li);
    });
    if(!rows.length) refs.list.appendChild(el("li","brb-msg","No products match all of those words. Try fewer words or one of the examples above."));
    refs.more.style.display=rows.length>shown?"":"none";
  }
  function start(){ if("IntersectionObserver" in window){
      var io=new IntersectionObserver(function(es){ if(es[0].isIntersecting){io.disconnect(); load();} },{rootMargin:"400px"}); io.observe(document.getElementById("br-bio"));
    } else load(); }
  if(document.readyState==="loading") document.addEventListener("DOMContentLoaded",start); else start();
})();
</script>
</section>
"""

BRIDGE_EDITS = [
    ('var mcpP=null; if(window.claude&&claude.use){mcpP=claude.use("mcp").catch(function(){return null;});}',
     'var mcpP=null; if(window.claude&&claude.use){mcpP=claude.use("mcp").catch(function(){return null;});}\n'
     '  else if(window.BMP&&BMP.on){mcpP=BMP.status().then(function(s){return s&&s.pubmed?BMP.mcp:null;});}'),
    ('var d=await sample.json(prompt(term),',
     'var d=sample.site?(await BMP.api("deepdive",{term:term},ctl.signal)).data\n        :await sample.json(prompt(term),'),
    ('var COPY={not_granted:"Claude access wasn',
     'var COPY={daily_limit:"You\'ve reached today\'s Deep Dive limit — it resets tomorrow.",budget_exhausted:"Deep Dive is resting until next month.",not_configured:"Deep Dive isn\'t switched on yet.",bad_term:"Try a shorter company or sector name.",upstream_error:"The connection dropped — try again.",not_granted:"Claude access wasn'),
    ('if(c==="not_granted"||c==="sampling_disabled"||c==="not_declared"){sample=null;off.hidden=false;}',
     'if(c==="not_granted"||c==="sampling_disabled"||c==="not_declared"||c==="budget_exhausted"||c==="not_configured"){sample=null;siteOff(c);}'),
    ('claude.use("sample").then(function(s){sample=s||null;if(!s)off.hidden=false;return claude.use("mcp");}).then(function(m){mcp=m||null;}).catch(function(){});\n  } else off.hidden=false;',
     'claude.use("sample").then(function(s){sample=s||null;if(!s)off.hidden=false;return claude.use("mcp");}).then(function(m){mcp=m||null;}).catch(function(){});\n'
     '  } else if(window.BMP&&BMP.on){\n'
     '    BMP.status().then(function(s){\n'
     '      if(s&&s.pubmed) mcp=BMP.mcp;\n'
     '      if(s&&s.claude) sample={site:true}; else siteOff(s&&s.reason);\n'
     '    });\n'
     '  } else off.hidden=false;\n'
     '  function siteOff(reason){\n'
     '    if(window.BMP&&BMP.on) off.textContent=reason==="budget_exhausted"?"Deep Dive has used this month\'s allowance and is resting until the 1st. Everything else on the site is up to date.":"Deep Dive is temporarily unavailable. Everything else on the site is up to date.";\n'
     '    off.hidden=false;\n'
     '  }'),
    ('var r=await sample([{role:"user",content:rules()}].concat(turns),opts);',
     'var r;\n      if(sample.site){var j=await BMP.api("ask",{turns:turns},ctl.signal);r={text:j.text,truncated:j.truncated};}\n'
     '      else r=await sample([{role:"user",content:rules()}].concat(turns),opts);'),
    ('var COPY={tools_unavailable:',
     'var COPY={daily_limit:"You\'ve reached today\'s question limit — it resets tomorrow.",budget_exhausted:"The assistant has used this month\'s allowance and is resting until the 1st.",not_configured:"The assistant isn\'t switched on yet.",bad_request:"That question couldn\'t be sent — try rephrasing.",tools_unavailable:'),
    ('var HIDE={not_granted:1,sampling_disabled:1,not_declared:1,capability_disabled:1,capability_removed:1};',
     'var HIDE={not_granted:1,sampling_disabled:1,not_declared:1,capability_disabled:1,capability_removed:1,budget_exhausted:1,not_configured:1};'),
    ('s.limits().catch(function(){return null;})]).then(function(r){mcp=r[0];canTools=!!(mcp&&r[1]&&r[1].tools);});\n    }).catch(function(){});\n  }',
     's.limits().catch(function(){return null;})]).then(function(r){mcp=r[0];canTools=!!(mcp&&r[1]&&r[1].tools);});\n    }).catch(function(){});\n'
     '  } else if(window.BMP&&BMP.on){\n'
     '    BMP.status().then(function(s){if(s&&s.claude){sample={site:true};canTools=true;fab.hidden=false;}});\n'
     '  }'),
]


def apply_bridge(page):
    if "window.BMP={" in page:
        return page  # already bridged
    missing = []
    for old, new in BRIDGE_EDITS:
        if page.count(old) != 1:
            missing.append(old[:60])
            continue
        page = page.replace(old, new)
    if missing:
        print("build_site: warning — bridge anchors not found (feature may stay claude.ai-only):", *missing, sep="\n  ")
    # bridge must load before any script that uses it
    body = page.find("<body")
    i = page.find("<script", body if body > -1 else 0)
    return page[:i] + BRIDGE_JS + page[i:]


# ---------------------------------------------------------------- page pieces
def find_panels(page):
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'<div class="tabpanel" id="(p-[a-z]+)"', page)]
    if len(starts) < 5:
        fail("could not find the tab panels")
    end_all = page.find("<footer", starts[-1][0])
    if end_all < 0:
        fail("could not find the footer")
    panels = {}
    for i, (pos, pid) in enumerate(starts):
        nxt = starts[i + 1][0] if i + 1 < len(starts) else end_all
        panels[pid] = (pos, nxt)
    return panels, starts[0][0], end_all


def nav_counts(page):
    counts = {}
    for m in re.finditer(r'aria-controls="(p-[a-z]+)"[^>]*>[^<]*<span class="pill">(\d+)</span>', page):
        counts[m.group(1)] = m.group(2)
    return counts


def href(slug, preview):
    if preview:
        return (slug or "overview") + ".html"
    return "/" + (slug + "/" if slug else "")


def build_nav(current_pid, counts, preview):
    links = []
    for slug, pid, label, *_ in PAGES:
        pill = f' <span class="pill">{counts[pid]}</span>' if pid in counts else ""
        cur = ' aria-current="page"' if pid == current_pid else ""
        links.append(f'    <a class="tab" href="{href(slug, preview)}"{cur}>{html.escape(label)}{pill}</a>')
    return ('<nav class="tabs" id="tabs" aria-label="Sections">\n' + "\n".join(links) + "\n  </nav>\n"
            '  <script>(function(){var c=document.querySelector(\'.tabs [aria-current="page"]\');'
            'if(c&&c.scrollIntoView)c.scrollIntoView({block:"nearest",inline:"center"});})();</script>')


SITE_CSS = """<style>
  /* multi-page site */
  .tabs .tab{text-decoration:none;display:inline-flex;align-items:center;}
  .tabs .tab[aria-current="page"] .pill{background:var(--accent-tint);color:var(--accent-ink);border-color:var(--accent-tint);}
  .brand h1 a,.brand .bn a{color:inherit;text-decoration:none;}
  .brand .bn{font-family:var(--f-display);font-weight:600;font-size:38px;line-height:1.05;margin:2px 0 0;letter-spacing:-.01em;display:block;}
  @media (max-width:560px){.brand .bn{font-size:30px;}}
  .site-foot{display:flex;flex-wrap:wrap;justify-content:space-between;gap:12px 24px;border-top:1px solid var(--line);margin-top:18px;padding-top:14px;font-size:12.5px;color:var(--muted);}
  .site-foot nav{display:flex;flex-wrap:wrap;gap:6px 16px;}
  .site-foot a{color:var(--muted);text-decoration:none;} .site-foot a:hover{color:var(--ink);text-decoration:underline;}
  .prose{max-width:72ch;font-size:15.5px;line-height:1.65;}
  .prose h2{font-family:var(--f-display);font-size:22px;margin:28px 0 8px;}
  .prose p,.prose li{color:var(--ink);} .prose ul{padding-left:20px;} .prose a{color:var(--tag-deal);}
  .nf{padding:48px 0;text-align:center;} .nf h2{font-family:var(--f-display);font-size:28px;margin:0 0 8px;}
</style>
"""

FAVICON = ("data:image/svg+xml," +
           "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='7' fill='%23141f19'/%3E"
           "%3Cpath d='M4 17h6l3-8 5 15 3-7h7' fill='none' stroke='%23e3be5c' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")


def head_tags(title, desc, slug, preview, edition_date_iso):
    url = SITE + "/" + (slug + "/" if slug else "")
    root = "" if preview else "/"
    t, d = html.escape(title), html.escape(desc)
    tags = [
        f"<title>{t}</title>",
        f'<meta name="description" content="{d}">',
        f'<link rel="canonical" href="{url}">',
        f'<link rel="icon" href="{root}favicon.svg" type="image/svg+xml">',
        f'<link rel="icon" href="{root}favicon.ico" sizes="any">',
        f'<link rel="apple-touch-icon" href="{root}apple-touch-icon.png">',
        f'<meta property="og:image" content="{SITE}/icon-512.png">',
        '<meta name="theme-color" content="#141f19">',
        f'<meta property="og:site_name" content="{NAME}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:title" content="{t}">',
        f'<meta property="og:description" content="{d}">',
        f'<meta property="og:url" content="{url}">',
        '<meta name="twitter:card" content="summary">',
        f'<meta name="bmp-api" content="{"api.php" if preview else "/api.php"}">',
    ]
    if not slug:
        ld = {"@context": "https://schema.org", "@type": "WebSite", "name": NAME, "url": SITE + "/",
              "description": desc}
        tags.append('<script type="application/ld+json">' + json.dumps(ld) + "</script>")
    if edition_date_iso:
        tags.append(f'<meta name="date" content="{edition_date_iso}">')
    return "\n".join(tags) + "\n"


def site_footer(preview):
    links = [f'<a href="{href(s, preview)}">{html.escape(l)}</a>' for s, _, l, *_ in PAGES]
    links.append(f'<a href="{href(ABOUT[0], preview)}">About</a>')
    year = datetime.date.today().year
    return ('\n  <div class="site-foot">\n    <nav aria-label="Site">' + " ".join(links) + "</nav>\n"
            f'    <div>© {year} {NAME} · For information only, not investment advice · <a href="{href(ABOUT[0], preview)}">About &amp; methodology</a></div>\n  </div>\n')


HASH_REDIRECT = """<script>
/* Old one-page links (/#pharma) go to the new page for that section. */
(function(){var m={overview:"%s",daily:"%s",biocat:"%s",pharma:"%s",ag:"%s",synbio:"%s",policy:"%s",reg:"%s",deep:"%s"};
var h=(location.hash||"").replace(/^#/,"");if(m[h]&&h!=="overview"){location.replace(m[h]);}})();
</script>
"""


def strip_tab_switcher(page):
    # The one-page tab switcher is not needed: each section is its own page.
    return re.sub(r"<script>\s*/\* ---- Tab switching:.*?</script>", "", page, count=1, flags=re.S)


def edition_meta(page):
    d = re.search(r'<span class="date">([^<]+)</span>', page)
    e = re.search(r"Edition No\. (\d+)", page)
    iso = ""
    if d:
        try:
            iso = datetime.datetime.strptime(d.group(1).strip(), "%A, %B %d, %Y").date().isoformat()
        except ValueError:
            pass
    return (d.group(1).strip() if d else ""), (e.group(1) if e else ""), iso


def add_listen_bar(page, out, preview):
    """Audio briefing player under the masthead on every page.
    Keeps a player already in the edition (from pulse_audio.py); otherwise builds one
    from the newest episode in OUT/feed.xml. Episode links are made site-absolute so
    they work from every page."""
    if '<section class="listen-bar"' not in page:
        feed = os.path.join(out, "feed.xml")
        if not os.path.isfile(feed):
            return page
        x = open(feed, encoding="utf-8").read()
        it = re.search(r"<item>(.*?)</item>", x, re.S)
        if not it:
            return page
        it = it.group(1)
        url = re.search(r'<enclosure url="([^"]+)"', it)
        dur = re.search(r"<itunes:duration>([^<]+)<", it)
        guid = re.search(r"biomarket-pulse-(\d{4}-\d{2}-\d{2})", it)
        if not url:
            return page
        name = url.group(1).rsplit("/", 1)[-1]
        if not preview and not os.path.isfile(os.path.join(out, name)):
            return page
        pretty = ""
        if guid:
            d = datetime.date.fromisoformat(guid.group(1))
            pretty = d.strftime("%A, %B ") + str(d.day) + d.strftime(", %Y")
        meta = " · ".join(v for v in (pretty, dur.group(1) if dur else "") if v)
        player = f"""
  <section class="listen-bar" aria-label="Audio briefing" style="display:flex;flex-wrap:wrap;align-items:center;gap:10px 16px;margin:-8px 0 22px;padding:12px 16px;border:1px solid var(--line);border-radius:10px;background:var(--surface);color:var(--ink)">
    <div style="flex:1 1 220px;min-width:0">
      <div style="font-weight:600">Listen to the latest briefing</div>
      <div style="color:var(--muted);font-size:.9em">{html.escape(meta)}{' · ' if meta else ''}<a href="/feed.xml" style="color:var(--accent-ink)">Podcast feed (RSS)</a></div>
    </div>
    <audio controls preload="none" src="{name}" style="flex:1 1 260px;max-width:100%;min-width:0"></audio>
  </section>
"""
        m = re.search(r'<header class="masthead">.*?</header>', page, re.S)
        if not m:
            return page
        page = page[:m.end()] + player + page[m.end():]
    if not preview:
        page = re.sub(r'(<section class="listen-bar".*?<audio[^>]*src=")(?!/|https?:)', r"\1/", page, count=1, flags=re.S)
        page = re.sub(r'(<section class="listen-bar".*?href=")https?://(?:www\.)?biomarketpulse\.com/feed\.xml', r"\1/feed.xml", page, count=1, flags=re.S)
    return page


def build(edition_path, out, preview=False):
    src = open(edition_path, encoding="utf-8").read()
    if "Denova" in src:
        fail("the edition mentions Denova — refusing to publish")
    full = apply_bridge(src)
    full = strip_tab_switcher(full)
    full = full.replace(".tabs button", ".tabs .tab").replace('.tabs .tab[aria-selected="true"]', '.tabs .tab[aria-current="page"]')
    # strip the page's own <title> (each page gets its own) and declare the language
    full = re.sub(r"<title>.*?</title>\s*", "", full, count=1, flags=re.S)
    full = re.sub(r"<html(?![^>]*\blang=)", '<html lang="en"', full, count=1)
    full = add_listen_bar(full, out, preview)
    panels, first, end_all = find_panels(full)
    counts = nav_counts(full)
    nav_m = re.search(r'<nav class="tabs" id="tabs".*?</nav>', full, re.S)
    if not nav_m:
        fail("could not find the tab bar")
    date_label, edition_no, date_iso = edition_meta(full)
    head_i = full.find("</head>")
    if head_i < 0:
        fail("no </head>")
    foot_end = full.find("</footer>", end_all)
    if foot_end < 0:
        fail("no </footer>")
    foot_end += len("</footer>")

    os.makedirs(out, exist_ok=True)
    written = []

    def page_html(title, desc, slug, current_pid, body_html, home=False):
        doc = full[:head_i] + head_tags(title, desc, slug, preview, date_iso) + SITE_CSS + full[head_i:]
        # re-find positions in doc (head grew)
        shift = len(doc) - len(full)
        nav_s, nav_e = nav_m.start() + shift, nav_m.end() + shift
        f0, f1 = first + shift, foot_end + shift
        before = doc[:nav_s] + build_nav(current_pid, counts, preview) + doc[nav_e:f0]
        if not home:
            before = before.replace("<h1>BioMarket Pulse</h1>",
                                    f'<span class="bn"><a href="{href("", preview)}">BioMarket Pulse</a></span>', 1)
        footer = doc[end_all + shift:f1]
        after = doc[f1:]
        extra = HASH_REDIRECT % tuple(href(s, preview) for s, *_ in PAGES) if home else ""
        return before + body_html + "\n  " + footer + site_footer(preview) + after.replace("</body>", extra + "</body>", 1)

    for slug, pid, label, title, desc in PAGES:
        if pid not in panels:
            print(f"build_site: warning — no panel {pid}; skipping {slug or 'home'}")
            continue
        a, b = panels[pid]
        body = full[a:b]
        body = re.sub(r'(<div class="tabpanel" id="%s")[^>]*>' % pid, r'\1>', body, count=1)  # visible, no tab roles
        if pid == "p-ag":
            mk = '<section class="rs" data-reg="ag"></section>'
            if mk in body:
                body = body.replace(mk, mk + "\n" + BR_SECTION, 1)
            else:
                print("build_site: warning — regulatory marker not found on Agriculture; registry section skipped")
        body = '<main id="main">\n  ' + body.strip() + "\n  </main>\n"
        doc = page_html(title, desc, slug, pid, body, home=(slug == ""))
        path = os.path.join(out, (slug or "overview") + ".html") if preview else \
            os.path.join(out, slug, "index.html") if slug else os.path.join(out, "index.html")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w", encoding="utf-8").write(doc)
        written.append(path)

    # About page
    about_body = f"""<main id="main">
  <section class="prose">
    <div class="section-head"><h2>About BioMarket Pulse</h2></div>
    <p><b>BioMarket Pulse</b> is a daily market-intelligence briefing on the businesses built on biology: pharma and biotech, synthetic biology, biocatalysis, and agriculture, with dedicated coverage of Brazil.</p>
    <p>Each morning's edition brings together the deals, product launches, regulatory decisions, clinical and field results, research papers and market moves that matter to executives, investors and scientists working across these sectors.</p>
    <h2>What's inside</h2>
    <ul>
      <li><a href="{href('', preview)}">Market Overview</a>: stock moves, a sector heatmap, the catalyst calendar and today's signals.</li>
      <li><a href="{href('daily-pulse', preview)}">Daily Pulse</a>: five things to know, the lead story and seven days of deal flow.</li>
      <li>Sector pages for <a href="{href('biocatalysis', preview)}">Biocatalysis</a>, <a href="{href('pharma-biotech', preview)}">Pharma &amp; Biotech</a>, <a href="{href('agriculture', preview)}">Agriculture</a>, <a href="{href('synthetic-biology', preview)}">Synthetic Biology</a> and <a href="{href('policy', preview)}">Policy &amp; Public Health</a>, each with analysis, a regulatory snapshot, the latest articles and new research papers.</li>
      <li><a href="{href('regulatory', preview)}">Regulatory Tracker</a>: products moving through FDA, EMA, EPA, EFSA, ANVISA, MAPA and CTNBio, from filing to decision.</li>
      <li><a href="{href('deep-dive', preview)}">Deep Dive</a>: an on-demand view of any company or sector's competitors, funding and recent news.</li>
    </ul>
    <h2>How each edition is made</h2>
    <p>Editions are compiled every morning (São Paulo time) from public sources, including company announcements, regulators, trade and scientific press, PubMed and market data providers, with the help of AI tools. Every item links to its source. Market data are end-of-day closes and may lag by a trading day; research-paper lists refresh live from PubMed.</p>
    <p>Deep Dive and Ask the Pulse are AI-generated on request. They can be incomplete or out of date, and they say so where it matters.</p>
    <h2>Important</h2>
    <p>BioMarket Pulse is for information only. It is not investment, legal, medical or agronomic advice. Check primary sources before acting on anything you read here.</p>
  </section>
</main>
"""
    doc = page_html(ABOUT[1] + " | " + NAME, ABOUT[2], ABOUT[0], None, about_body)
    path = os.path.join(out, "about.html") if preview else os.path.join(out, "about", "index.html")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w", encoding="utf-8").write(doc)
    written.append(path)

    # 404
    nf_body = f"""<main id="main"><section class="nf"><h2>Page not found</h2>
  <p>That page isn't here. Try <a href="{href('', preview)}">today's Market Overview</a> or pick a section above.</p></section></main>
"""
    doc = page_html("Page not found | " + NAME, "Page not found.", "404", None, nf_body)
    doc = doc.replace('<link rel="canonical" href="' + SITE + '/404/">\n', '<meta name="robots" content="noindex">\n')
    open(os.path.join(out, "404.html"), "w", encoding="utf-8").write(doc)
    written.append(os.path.join(out, "404.html"))

    if not preview:
        # full edition for api.php (Deep Dive / Ask the Pulse context); not public
        os.makedirs(os.path.join(out, "data"), exist_ok=True)
        open(os.path.join(out, "data", "edition.html"), "w", encoding="utf-8").write(full)
        open(os.path.join(out, "data", ".htaccess"), "w").write("Require all denied\nDeny from all\n")
        lastmod = date_iso or datetime.date.today().isoformat()
        urls = [SITE + "/" + (s + "/" if s else "") for s, *_ in PAGES] + [SITE + "/about/"]
        sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
        for u in urls:
            sm.append(f"  <url><loc>{u}</loc><lastmod>{lastmod}</lastmod><changefreq>daily</changefreq></url>")
        sm.append("</urlset>")
        open(os.path.join(out, "sitemap.xml"), "w").write("\n".join(sm) + "\n")
        open(os.path.join(out, "robots.txt"), "w").write(
            f"User-agent: *\nDisallow: /data/\nDisallow: /tools/\nDisallow: /api.php\n\nSitemap: {SITE}/sitemap.xml\n")
    print(f"build_site: Edition {edition_no} ({date_label}) → {len(written)} pages in {out}")
    return written


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        fail(__doc__)
    out = args[1] if len(args) > 1 else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    build(args[0], out, preview="--preview" in sys.argv)
