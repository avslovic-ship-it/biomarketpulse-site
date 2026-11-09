"""Ontology example page: one patent-to-price thread (Novo Nordisk oral semaglutide) and the
R&D, M&A and investment insights read from it. Facts were checked by hand on November 8, 2026.
build_site.py calls build() after the section pages exist, so the page always wears the current header."""
import json, os, re, html
E = html.escape
HERE = os.path.dirname(os.path.abspath(__file__))


def build(OUT, preview):
    bars = json.load(open(os.path.join(HERE, "ontology_nvo.json")))
    about = os.path.join(OUT, "about.html" if preview else "about/index.html")
    if not os.path.exists(about):
        return
    tpl = open(about).read()
    _render(OUT, preview, bars, tpl)


def _render(OUT, preview, bars, tpl):

    # ---- candlestick svg (NVO, Aug 6 – Nov 6, 2026) ----
    W, H, L, R, T, B = 1000, 300, 56, 16, 20, 36
    lo = min(b[3] for b in bars); hi = max(b[2] for b in bars)
    lo, hi = lo - 0.5, hi + 0.5
    n = len(bars); step = (W - L - R) / n; bw = max(step * 0.62, 2)
    X = lambda i: L + step * i + step / 2
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    parts = []
    for g in range(int(lo) + 1, int(hi) + 1):
        if g % 2: continue
        parts.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(g):.1f}" y2="{Y(g):.1f}" stroke="#E3E8ED"/><text x="{L-8}" y="{Y(g)+4:.1f}" text-anchor="end" font-size="12" fill="#4A5B6C">${g}</text>')
    months = {"08": "Aug", "09": "Sep", "10": "Oct", "11": "Nov"}
    seen = set()
    for i, b in enumerate(bars):
        m = b[0][5:7]
        if m not in seen and int(b[0][8:]) <= 7:
            seen.add(m); parts.append(f'<text x="{X(i):.1f}" y="{H-12}" text-anchor="middle" font-size="12" fill="#4A5B6C">{months[m]} {int(b[0][8:])}</text>')
    gi = next(i for i, b in enumerate(bars) if b[0] == "2026-11-04")
    parts.append(f'<rect x="{X(gi)-step/2:.1f}" y="{T}" width="{step:.1f}" height="{H-T-B}" fill="#E6EEFB"/>')
    for i, (d, o, h_, l_, c, v) in enumerate(bars):
        up = c >= o; col = "#1E7A4C" if up else "#B4560F"
        y1, y2 = Y(max(o, c)), Y(min(o, c))
        parts.append(f'<g><title>{d}: open {o}, high {h_}, low {l_}, close {c}</title><line x1="{X(i):.1f}" x2="{X(i):.1f}" y1="{Y(h_):.1f}" y2="{Y(l_):.1f}" stroke="{col}"/><rect x="{X(i)-bw/2:.1f}" y="{y1:.1f}" width="{bw:.1f}" height="{max(y2-y1,1):.1f}" fill="{col}"/></g>')
    gx, gy = X(gi), Y(bars[gi][2])
    parts.append(f'<line x1="{gx:.1f}" x2="{gx-120:.1f}" y1="{gy-6:.1f}" y2="{gy-6:.1f}" stroke="#1F5FC4"/><text x="{gx-126:.1f}" y="{gy-2:.1f}" text-anchor="end" font-size="13" font-weight="700" fill="#0E2236">Nov 4: guidance raised, +5.0% on 2.5× volume</text>')
    svg = f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Novo Nordisk (NVO) daily candles, August 6 to November 6, 2026; jump on November 4" style="width:100%;height:auto;display:block">{"".join(parts)}</svg>'

    # ---- the five entities ----
    NODES = [
     ("patent", "Patent", "#7D5BC0", "US 12,514,822 B2", "Oral dosing of GLP-1 compounds",
      [("Assignee", "Novo Nordisk A/S"), ("Inventors", "Flemming S. Nielsen, Per Sauerberg"), ("Published", "January 6, 2026"),
       ("Claims", "Oral semaglutide with the SNAC absorption enhancer at 0.5–50 mg; dependent claims narrow the patients to people with obesity"),
       ("Family", "Same title and inventors as US 10,278,923 (2019) and US 12,239,739 (2025)")],
      [("Patent summary (MTEC)", "https://mtec-sc.org/patents/US-12514822-B2"), ("US 12,239,739 in the USPTO Official Gazette", "https://patentsgazette.uspto.gov/week09/OG/html/1532-1/US12239739-20250304.html")]),
     ("paper", "Paper", "#0E9384", "OASIS 4, N Engl J Med", "Oral semaglutide 25 mg in adults with overweight or obesity",
      [("Authors", "Wharton S, Lingvay I, Bogdanski P, et al."), ("Published", "September 18, 2025; 393(11):1077–1087"), ("Design", "307 adults without diabetes, randomized 2:1, 64 weeks, placebo-controlled"),
       ("Result", "Body weight −13.6% with oral semaglutide vs −2.2% with placebo at week 64"), ("IDs", "PMID 40934115 · DOI 10.1056/NEJMoa2500969 · NCT05564117")],
      [("PubMed record", "https://pubmed.ncbi.nlm.nih.gov/40934115/"), ("DOI", "https://doi.org/10.1056/NEJMoa2500969")]),
     ("drug", "Drug", "#1F5FC4", "Semaglutide, oral", "GLP-1 receptor agonist tablet co-formulated with SNAC",
      [("Owner", "Novo Nordisk"), ("Mechanism", "GLP-1 receptor agonist"), ("Formulation", "Tablet with salcaprozate sodium (SNAC), which enables absorption in the stomach"),
       ("Other products", "Rybelsus tablets for type 2 diabetes (FDA, September 2019); Ozempic and Wegovy injections")],
      [("FDA non-clinical review of oral semaglutide and SNAC", "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2019/213051Orig1s000PharmR.pdf")]),
     ("product", "Product", "#C8691E", "Wegovy pill 25 mg", "First oral GLP-1 approved for weight management",
      [("Dose", "Once-daily oral semaglutide 25 mg"), ("US approval", "FDA, December 22, 2025: weight reduction and lower risk of major cardiovascular events"),
       ("Brazil approval", "ANVISA, November 4, 2026: Brazil's first oral GLP-1 for weight loss"), ("US launch", "Early January 2026")],
      [("Novo Nordisk press release, Dec 22, 2025", "https://www.novonordisk.com/news-and-media/news-and-ir-materials/news-details.html?id=916472"),
       ("ANVISA approval, Jornal do Comércio", "https://www.jornaldocomercio.com/geral/2026/11/1269233-caneta-emagrecedora-em-pilula-anvisa-aprova-versao-em-comprimido-do-wegovy.html")]),
     ("move", "Market move", "#1E7A4C", "NVO +5.0%, Nov 4, 2026", "Novo Nordisk raised 2026 guidance after an oral Wegovy sales beat",
      [("Nov 4 close", "$42.18, up 5.0% from $40.19"), ("Volume", "26.0 million shares, 2.5 times the 20-day average of 10.2 million"),
       ("After", "Closed $40.31 on Nov 6, giving back 4.4%; the week ended up 0.8%"), ("Cause", "Guidance raised on November 4 after an oral Wegovy sales beat, as reported in the daily edition")],
      [("Price history: daily closes and volumes in the edition's chart data", "#move-chart")]),
    ]
    EDGES = ["claims the dose tested in", "is the pivotal trial of", "is sold as", "sales beat moved"]
    EDGE_NOTES = ["25 mg sits inside the patent's claimed 0.5–50 mg range", "OASIS 4 supports the 25 mg weight-loss label", "Wegovy pill = semaglutide 25 mg tablet", "Guidance raised Nov 4 on oral Wegovy sales"]

    cards = []
    for i, (key, typ, col, name, sub, facts, src) in enumerate(NODES):
        cards.append(f'''<button type="button" class="on-node" data-k="{key}" aria-pressed="{'true' if i == 0 else 'false'}" aria-controls="on-detail" style="--c:{col}">
    <span class="on-type"><i aria-hidden="true"></i>{E(typ)}</span><b>{E(name)}</b><span class="on-sub">{E(sub)}</span></button>''')
        if i < len(EDGES):
            cards.append(f'<div class="on-edge" aria-hidden="true"><span>{E(EDGES[i])}</span><svg viewBox="0 0 40 12" width="40" height="12"><path d="M0 6H34" stroke="#9AA8B5" stroke-width="1.5"/><path d="M32 1l7 5l-7 5z" fill="#9AA8B5"/></svg></div>')
    details = []
    for i, (key, typ, col, name, sub, facts, src) in enumerate(NODES):
        rel = ""
        if i > 0: rel += f'<p class="on-rel">← <b>{E(NODES[i-1][3])}</b> {E(EDGES[i-1])} this: {E(EDGE_NOTES[i-1])}.</p>'
        if i < len(EDGES): rel += f'<p class="on-rel">→ This {E(EDGES[i])} <b>{E(NODES[i+1][3])}</b>: {E(EDGE_NOTES[i])}.</p>'
        rows = "".join(f'<tr><th scope="row">{E(a)}</th><td>{E(b)}</td></tr>' for a, b in facts)
        links = "".join(f'<li><a href="{E(u)}"{"" if u.startswith("#") else " target=\"_blank\" rel=\"noopener\""}>{E(t)}</a></li>' for t, u in src)
        details.append(f'''<div class="on-card" data-k="{key}"{'' if i == 0 else ' hidden'} style="--c:{col}">
    <p class="on-type"><i aria-hidden="true"></i>{E(typ)}</p><h3>{E(name)}</h3><p class="on-lead">{E(sub)}</p>
    <table class="on-facts">{rows}</table>{rel}<p class="on-src-h">Sources</p><ul class="on-src">{links}</ul></div>''')

    schema_rows = [("Patent", "Number, assignee, title, claim summary, publication date, family", "EPO Open Patent Services feed, USPTO"),
                   ("Paper", "Title, journal, date, DOI, PMID, trial ID, result", "PubMed"),
                   ("Drug", "Name, owner, mechanism, formulation", "Curated with each edition"),
                   ("Product", "Brand, dose, indication, approvals by agency and date", "Regulatory Tracker"),
                   ("Market move", "Ticker, date, % change, volume against average, cause", "Daily price history and the edition")]
    rel_rows = [("claims the dose tested in", "Patent → Paper", "The tested dose falls inside the claimed range"),
                ("is the pivotal trial of", "Paper → Drug", "The trial supports the drug's approved use"),
                ("is sold as", "Drug → Product", "The product's active ingredient and dose"),
                ("approved by", "Product → Agency", "Agency, date and indication, from the Regulatory Tracker"),
                ("sales beat moved", "Product → Market move", "The company's own explanation, dated the same day")]
    schema = "".join(f"<tr><th scope='row'>{E(a)}</th><td>{E(b)}</td><td>{E(c)}</td></tr>" for a, b, c in schema_rows)
    rels = "".join(f"<tr><th scope='row'>{E(a)}</th><td>{E(b)}</td><td>{E(c)}</td></tr>" for a, b, c in rel_rows)


    INSIGHTS = [
     ("rd", "R&D", "#1F5FC4", "Formulation IP is now the franchise moat, not the molecule",
      "Semaglutide's molecule patent expired in Brazil in March 2026 and generic pens followed by August. Novo's newer claims sit on how the drug is delivered: oral dosing with the SNAC absorption enhancer, granted as recently as January 2026. The Wegovy pill reached Brazil in November on that delivery platform.",
      [("Patent", "US 12,514,822 (oral SNAC dosing, 2026)"), ("claims the dose tested in", ""), ("Product", "Wegovy pill, ANVISA Nov 4, 2026"), ("contrasts with", ""), ("Drug event", "Molecule patent expired in Brazil, Mar 2026")],
      "Whether the SNAC formulation patents are granted and in force in Brazil (INPI) is not yet verified.",
      [("Generic semaglutide approved in Brazil, Rio Times", "https://www.riotimesonline.com/brazil-approves-its-first-locally-made-generic-of-semaglutide-the-ozempic-weight-loss-drug/"), ("Patent summary (MTEC)", "https://mtec-sc.org/patents/US-12514822-B2")]),
     ("rd", "R&D", "#1F5FC4", "Oral obesity drugs now compete on how easy they are to take",
      "OASIS 4 reported 13.6% weight loss at 64 weeks with the Wegovy pill; Lilly's ATTAIN-1 reported 12.4% at 72 weeks with the top dose of Foundayo. The trials differ, so the numbers are not a head-to-head result. Foundayo's label carries no food or water restrictions, the point Lilly used to set it apart.",
      [("Paper", "OASIS 4, NEJM 2025"), ("is the pivotal trial of", ""), ("Product", "Wegovy pill"), ("competes with", ""), ("Product", "Foundayo (orforglipron), FDA Apr 1, 2026")],
      "Real-world persistence data on both pills, and the European Commission decision on Foundayo after its October 15 CHMP opinion.",
      [("OASIS 4 on PubMed", "https://pubmed.ncbi.nlm.nih.gov/40934115/"), ("Foundayo FDA approval, Healio", "https://www.healio.com/news/endocrinology/20260401/fda-approves-orforglipron-an-oral-glp1-for-adults-with-obesity")]),
     ("ma", "M&A", "#C8691E", "Big pharma is still paying up for obesity assets",
      "On November 4, the day Novo raised guidance on the Wegovy pill, AstraZeneca reportedly made a ~$10B unsolicited bid for Rhythm Pharmaceuticals. Lilly's oral GLP-1 itself came through licensing: Chugai discovered orforglipron and licensed it to Lilly. Owners of differentiated obesity mechanisms remain both licensing partners and takeover candidates.",
      [("Product", "Wegovy pill"), ("sales beat moved", ""), ("Market move", "NVO, Nov 4"), ("same day as", ""), ("Deal", "AstraZeneca ~$10B bid for Rhythm")],
      "Whether rival bidders emerge for Rhythm, as analysts expect, and which mid-cap obesity programs draw licensing interest next.",
      [("AstraZeneca bid for Rhythm, Reuters via WSAU", "https://wsau.com/2026/11/04/astrazeneca-made-10-billion-bid-for-obesity-drugmaker-rhythm-wsj-reports/"), ("Chugai on the Foundayo approval", "https://chemxplore.com/news/lilly-foundayo-orforglipron-fda-approval")]),
     ("ma", "M&A", "#C8691E", "Brazil's generic makers are scaling up around semaglutide",
      "EMS bought Sanofi's Brazilian generics unit Medley in March 2026 and launched its semaglutide copy at about 30% below Ozempic. Hypera plans its own version, and Biomm sells one licensed from India's Biocon. Peptide API and pen-device suppliers, and Latin American distribution, are where partnership and deal activity is building.",
      [("Drug event", "Molecule patent expired in Brazil, Mar 2026"), ("opened the market to", ""), ("Companies", "EMS, Hypera, Biomm with Biocon"), ("compete with", ""), ("Product", "Ozempic and Wegovy in Brazil")],
      "ANVISA decisions on the remaining semaglutide applications, and CADE's review of EMS's Medley acquisition.",
      [("EMS after the Medley deal, Reuters", "https://d2233.cms.socastsrm.com/?p=2482261"), ("EMS launches first Ozempic copy, GxP News", "https://gxpnews.net/en/2026/05/novo-nordisk-faces-first-ozempic-competition-in-brazil-as-local-drugmaker-ems-launches-copy/")]),
     ("inv", "Investment", "#1E7A4C", "The market treated the guidance raise as a one-day event",
      "NVO rose 5.0% on November 4 on 2.5 times its usual volume, then gave back 4.4% in two sessions and ended the week up 0.8%, still below its early-August level near $46. Investors appear to weigh the oral launch against competition from Foundayo and generic semaglutide in markets such as Brazil.",
      [("Product", "Wegovy pill"), ("sales beat moved", ""), ("Market move", "NVO +5.0%, faded by Nov 6"), ("weighed against", ""), ("Products", "Foundayo; generic semaglutide in Brazil")],
      "Next quarter's oral Wegovy prescriptions, the EU decisions on oral semaglutide 25 mg and on Foundayo, and generic pricing in Brazil.",
      [("Price history: daily candles above", "#move-chart"), ("Novo Nordisk press release, Dec 22, 2025", "https://www.novonordisk.com/news-and-media/news-and-ir-materials/news-details.html?id=916472")]),
    ]
    RULES = [
     ("Molecule patent expires while a newer formulation or dosing patent covers a newly approved product", "R&D", "Lifecycle and delivery-platform insight", "Insight 1"),
     ("Two products with the same target are approved for the same use within 12 months", "R&D", "Competitive positioning insight", "Insight 2"),
     ("A large deal in the same therapy area lands within 7 days of a product event", "M&A", "Deal appetite insight", "Insight 3"),
     ("A patent expiry is followed by approvals for several local copies", "M&A", "Consolidation and partner-search insight", "Insight 4"),
     ("A stock moves on more than twice its average volume and reverses within 3 sessions", "Investment", "Event-faded insight, with the open risks it points to", "Insight 5"),
    ]
    def insights_html():
        btn = ('<div class="dk-filters" role="group" aria-label="Filter insights by type">'
               '<button type="button" aria-pressed="true" data-f="">All<span class="n">5</span></button>'
               '<button type="button" aria-pressed="false" data-f="rd">R&amp;D<span class="n">2</span></button>'
               '<button type="button" aria-pressed="false" data-f="ma">M&amp;A<span class="n">2</span></button>'
               '<button type="button" aria-pressed="false" data-f="inv">Investment<span class="n">1</span></button></div>')
        cards = []
        for i, (k, lab, col, head, body, path, watch, src) in enumerate(INSIGHTS):
            chain = []
            for a, b in path:
                if b: chain.append(f'<span class="in-node"><small>{E(a)}</small>{E(b)}</span>')
                else: chain.append(f'<span class="in-edge">{E(a)} →</span>')
            links = "".join(f'<li><a href="{E(u)}"{"" if u.startswith("#") else " target=\"_blank\" rel=\"noopener\""}>{E(t)}</a></li>' for t, u in src)
            cards.append(f'''<article class="in-card" data-t="{k}" style="--c:{col}"><p class="on-type"><i aria-hidden="true"></i>{lab} insight {i+1}</p>
    <h3>{E(head)}</h3><p class="in-body">{E(body)}</p><p class="in-h">Evidence path</p><div class="in-path">{"".join(chain)}</div>
    <p class="in-h">What to watch</p><p class="in-watch">{E(watch)}</p><p class="in-h">Sources</p><ul class="on-src">{links}</ul></article>''')
        rules = "".join(f"<tr><th scope='row'>{E(a)}</th><td>{E(b)}</td><td>{E(c)}</td><td>{E(d)}</td></tr>" for a, b, c, d in RULES)
        return (f'''<section aria-labelledby="in-h"><h2 class="dk-h2" id="in-h">Insights from the graph</h2>
    <p class="dk-sub">Each insight is built by following links in the graph, including neighbors of the five entities above: a competing product, a deal and the Brazilian generic makers. Links checked by hand on November 8, 2026. Analysis only, not investment advice.</p>
    {btn}<div class="in-grid">{"".join(cards)}</div>
    </section>''')

    CSS = """<style>
    .on-chain{display:flex;flex-wrap:wrap;align-items:stretch;gap:10px 0;margin:0 0 20px;}
    .on-node{flex:1 1 170px;min-width:0;text-align:left;font:inherit;background:#fff;border:0;border-radius:16px;padding:16px 16px 18px;box-shadow:0 0 0 1px var(--line);cursor:pointer;display:flex;flex-direction:column;gap:6px;color:var(--ink);min-height:44px;}
    .on-node:hover{box-shadow:0 0 0 2px var(--c);}
    .on-node[aria-pressed="true"]{box-shadow:0 0 0 2px var(--c),0 6px 18px rgba(14,34,54,.10);}
    .on-node b{font-size:18px;font-weight:800;line-height:1.2;letter-spacing:-.01em;}
    .on-sub{font-size:14px;color:var(--muted);line-height:1.4;}
    .on-type{display:flex;align-items:center;gap:8px;font-size:13px;font-weight:700;color:var(--c);margin:0;}
    .on-type i{width:10px;height:10px;border-radius:50%;background:var(--c);display:block;}
    .on-edge{flex:0 0 92px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;padding:0 4px;text-align:center;font-size:12px;line-height:1.25;color:var(--muted);}
    .on-card{background:#fff;border-radius:20px;padding:24px 28px;box-shadow:0 0 0 1px var(--line);}
    .on-card h3{margin:6px 0 4px;font-size:28px;font-weight:800;letter-spacing:-.02em;}
    .on-lead{margin:0 0 16px;font-size:17px;color:var(--muted);}
    .on-facts{border-collapse:collapse;width:100%;max-width:820px;font-size:15px;}
    .on-facts th{text-align:left;font-weight:700;color:var(--ink);padding:10px 16px 10px 0;width:150px;vertical-align:top;border-top:1px solid var(--line);}
    .on-facts td{padding:10px 0;border-top:1px solid var(--line);line-height:1.5;}
    .on-rel{margin:14px 0 0;font-size:15px;line-height:1.5;}
    .on-src-h{margin:18px 0 6px;font-size:14px;font-weight:700;color:var(--muted);}
    .on-src{margin:0;padding-left:18px;font-size:14px;line-height:1.7;}
    .on-panel{background:#fff;border-radius:20px;padding:18px 24px 14px;box-shadow:0 0 0 1px var(--line);}
    .on-table{border-collapse:collapse;width:100%;font-size:15px;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 0 0 1px var(--line);}
    .on-table th,.on-table td{text-align:left;padding:12px 16px;border-top:1px solid var(--line);vertical-align:top;line-height:1.45;}
    .on-table thead th{border-top:0;background:#F0F4F7;font-size:14px;}
    .on-table tbody th{font-weight:700;white-space:nowrap;}
    .on-scroll{overflow-x:auto;}
    .in-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:14px;margin-top:6px;}
    .in-card{background:#fff;border-radius:18px;padding:20px 22px;box-shadow:0 0 0 1px var(--line);border-top:4px solid var(--c);}
    .in-card[hidden]{display:none;}
    .in-card h3{margin:6px 0 8px;font-size:21px;font-weight:800;line-height:1.25;letter-spacing:-.01em;}
    .in-body{margin:0;font-size:15.5px;line-height:1.6;}
    .in-h{margin:14px 0 6px;font-size:13px;font-weight:700;color:var(--muted);}
    .in-path{display:flex;flex-wrap:wrap;align-items:center;gap:6px;}
    .in-node{display:inline-flex;flex-direction:column;background:#F0F4F7;border-radius:10px;padding:6px 10px;font-size:13.5px;font-weight:600;line-height:1.3;}
    .in-node small{font-size:11.5px;font-weight:600;color:var(--muted);}
    .in-edge{font-size:12.5px;color:var(--muted);}
    .in-watch{margin:0;font-size:15px;line-height:1.5;}
    .in-rules-h{margin:36px 0 4px;font-size:22px;font-weight:800;letter-spacing:-.01em;}
    @media (max-width:760px){.in-grid{grid-template-columns:minmax(0,1fr);}}
    .on-qs{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;list-style:none;padding:0;margin:0;}
    .on-qs li{background:#fff;border-radius:16px;padding:18px 20px;box-shadow:0 0 0 1px var(--line);font-size:16px;line-height:1.45;}
    .on-qs b{display:block;font-size:17px;margin-bottom:6px;}
    @media (max-width:760px){.on-chain{flex-direction:column;}.on-edge{flex-basis:auto;flex-direction:row;padding:6px 0;}.on-edge svg{transform:rotate(90deg);}.on-card{padding:20px;}.on-facts th{width:110px;}}
    </style>"""
    JS = """<script>
    (function(){var fb=document.querySelector('#in-h')&&document.querySelector('#in-h').parentNode.querySelector('.dk-filters');
    if(fb){fb.addEventListener('click',function(e){var b=e.target.closest('button');if(!b)return;[].forEach.call(fb.querySelectorAll('button'),function(x){x.setAttribute('aria-pressed',x===b?'true':'false');});
    [].forEach.call(document.querySelectorAll('.in-card'),function(c){c.hidden=!!b.dataset.f&&c.dataset.t!==b.dataset.f;});});}})();
    (function(){var ns=[].slice.call(document.querySelectorAll('.on-node')),cs=[].slice.call(document.querySelectorAll('.on-card'));
    ns.forEach(function(b){b.addEventListener('click',function(){ns.forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false');});cs.forEach(function(c){c.hidden=c.dataset.k!==b.dataset.k;});});});})();
    </script>"""

    main = f'''
    <main id="main">
    <section aria-labelledby="on-chain-h"><h2 class="dk-h2" id="on-chain-h">The chain</h2>
    <p class="dk-sub">Five entities, four typed links. Select any one to see its facts, its links and its sources.</p>
    <div class="on-chain">{"".join(cards)}</div>
    <div id="on-detail" aria-live="polite">{"".join(details)}</div></section>
    <section id="move-chart" aria-labelledby="on-move-h"><h2 class="dk-h2" id="on-move-h">The market move</h2>
    <p class="dk-sub">Novo Nordisk (NVO) daily candles, August 6 to November 6, 2026. Each candle is green when the stock closed above its open and orange when it closed below; the guidance day is shaded. On November 4 NVO opened at $42.45 and closed at $42.18, so its candle is orange even though it ended 5.0% above the previous close.</p>
    <div class="on-panel">{svg}</div></section>
    <section aria-labelledby="on-schema-h"><h2 class="dk-h2" id="on-schema-h">The ontology behind it</h2>
    <p class="dk-sub">Every entity has a type and fields; every link has a type, a direction and the evidence for it.</p>
    <div class="on-scroll"><table class="on-table"><thead><tr><th scope="col">Entity</th><th scope="col">Key fields</th><th scope="col">Where BioMarket Pulse gets it</th></tr></thead><tbody>{schema}</tbody></table></div>
    <div class="on-scroll" style="margin-top:16px"><table class="on-table"><thead><tr><th scope="col">Relation</th><th scope="col">From → to</th><th scope="col">Evidence stored with it</th></tr></thead><tbody>{rels}</tbody></table></div></section>
    {insights_html()}
    
    </main>
    '''
    page = re.sub(r'<main id="main">.*?</main>', lambda m: main, tpl, count=1, flags=re.S)
    page = page.replace('<span aria-current="page">About &amp; methodology</span>', '<span aria-current="page">Ontology example</span>')
    page = re.sub(r'(<p class="dk-eyebrow">)[^<]*(</p>)', r'\1Ontology example\2', page, count=1)
    page = re.sub(r'<h1>[^<]*</h1>', '<h1>One thread from patent to price</h1>', page, count=1)
    page = re.sub(r'(<p class="dk-topics">)[^<]*(</p>)', r'\1How BioMarket Pulse can link its datasets, from a Novo Nordisk patent to the stock move, and turn the links into R&D, M&A and investment insights.\2', page, count=1)
    page = re.sub(r'<section class="listen-bar".*?</section>', '', page, count=1, flags=re.S)
    page = page.replace('<title>', '<title>Ontology example: patent to price | ', 1)
    page = re.sub(r'<title>Ontology example: patent to price \| [^<]*</title>', '<title>Ontology example: patent to price | BioMarket Pulse</title>', page, count=1)
    page = page.replace("</head>", CSS + "</head>", 1).replace("</body>", JS + "</body>", 1)
    page = page.replace('<a href="about.html" aria-current="true">About</a>', '<a href="about.html">About</a>')
    tab_href = "ontology.html" if preview else "/ontology/"
    page = page.replace(f'<a href="{tab_href}">', f'<a href="{tab_href}" aria-current="page" style="border-bottom-color:#7D5BC0">', 1)
    page = re.sub(r'(<nav class="dk-gnav"[^>]*>.*?)</nav>', lambda m: m.group(0).replace(' aria-current="page"', ''), page, count=1, flags=re.S)
    if preview:
        open(os.path.join(OUT, "ontology.html"), "w").write(page)
    else:
        os.makedirs(os.path.join(OUT, "ontology"), exist_ok=True)
        open(os.path.join(OUT, "ontology", "index.html"), "w").write(page)

