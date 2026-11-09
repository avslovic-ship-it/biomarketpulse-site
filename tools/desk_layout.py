"""Research-desk page template for BioMarket Pulse (design direction D).

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
        "watch_tape": None,
        "page_tape": "cm",  # show the Commodities ticker at the top of this page
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

# Non-desk pages get the same frame (header, desk tabs, title band) with their content unchanged.
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
    ("ontology", "p-onto", "Ontology example"),
]
DISCOVER_NAV = [("deep-dive", "Deep Dive"), ("", "Market Overview"), ("daily-pulse", "Daily Pulse")]
REG_KEY = {"p-biocat": "biocat", "p-pharma": "pharma", "p-ag": "ag", "p-synbio": "synbio", "p-policy": "policy"}


# Desk identity colours (validated categorical set: blue, orange, teal, violet)
DESK_COLOR = {"p-biocat": "#C8691E", "p-pharma": "#1F5FC4", "p-ag": "#0E9384", "p-brbio": "#0E9384",
              "p-synbio": "#7D5BC0", "p-policy": "#4A5B6C", "p-reg": "#0E2236", "p-onto": "#7D5BC0"}

# Article types -> four groups for the "at a glance" bar (fixed order, fixed colours)
ART_GROUPS = [
    ("Deals", "#1F5FC4", {"M&A", "Licensing", "Funding", "IPO", "Partnership", "Acquisition", "Deal", "Deals"}),
    ("Clinical, research and risk", "#C8691E", None),          # everything not matched elsewhere
    ("Approvals and launches", "#0E9384", {"Approval", "Regulatory", "New product", "New products", "Launch", "Product"}),
    ("Ended or terminated", "#7D5BC0", {"Terminated", "Deal ended", "Deals ended", "Ended"}),
]

# Groups for the overview well plate (the edition's biotech universe)
PLATE_GROUPS = [["Large-cap biotech", ["AMGN", "GILD", "VRTX", "REGN"]], ["Neuro", ["BIIB", "NBIX"]],
                ["RNA medicines", ["ALNY", "IONS", "ARWR"]], ["mRNA & vaccines", ["MRNA", "BNTX"]],
                ["Gene editing", ["CRSP", "BEAM", "NTLA"]], ["Oncology", ["RVMD", "EXEL", "INCY", "GMAB"]],
                ["Immunology & rare", ["ARGX", "INSM", "BMRN", "BBIO", "UTHR", "ROIV"]]]

FONT_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Schibsted+Grotesk:wght@400;500;600;700;800;900&display=swap">')

DESK_CSS = r"""<style id="desk-layout">
/* Direction D: deal-sheet type, well-plate colours. Green = up, orange = down, blue = brand. */
body.desk{
  --ink:#0E2236; --muted:#4A5B6C; --faint:#5F6D7A; --line:#D9E0E6; --line-strong:#C3CDD6;
  --paper:#F7F9FB; --surface:#FFFFFF; --surface-2:#F0F4F7; --rule:#0E2236;
  --accent:#1F5FC4; --accent-ink:#174C9E; --accent-tint:#E6EEFB;
  --hl:#1F5FC4; --hl-ink:#174C9E; --hl-tint:#E6EEFB;
  --up:#1E7A4C; --down:#B4560F;
  --tk-bg:#0E2236; --tk2-bg:#0E2236; --tk-fg:#E4ECF5; --tk-sym:#FFFFFF; --tk-up:#7FE0A8; --tk-down:#F3B489; --tk-sep:#1C3550;
  --f-sans:'Schibsted Grotesk',system-ui,sans-serif; --f-display:'Schibsted Grotesk',system-ui,sans-serif;
  background:var(--paper); color:var(--ink);
}
body.desk, body.desk *:not(svg):not(svg *){font-family:'Schibsted Grotesk',system-ui,sans-serif !important;}
body.desk .up,body.desk .pos{color:var(--up);} body.desk .dn,body.desk .down,body.desk .neg{color:var(--down);}
body.desk .tape,body.desk .tape.bio{background:var(--tk-bg);border-bottom:1px solid #1C3550;}
body.desk .tape::before,body.desk .tape.bio::before{background:linear-gradient(90deg,var(--tk-bg),transparent);}
body.desk .tape::after,body.desk .tape.bio::after{background:linear-gradient(270deg,var(--tk-bg),transparent);}
body.desk .tape-lbl{background:var(--tk-bg);color:#9FB2C8;text-transform:none;letter-spacing:0;font-size:13px;white-space:nowrap;width:auto !important;max-width:none !important;padding-right:18px !important;z-index:3;box-shadow:12px 0 12px -4px var(--tk-bg);}
body.desk .tape .tk.asof{display:none !important;}
body.desk .tk{min-height:24px;}
body.desk .wrap{max-width:none;margin:0;padding:0;background:transparent;border:0;}
body.desk a:focus-visible,body.desk button:focus-visible,body.desk summary:focus-visible{outline:2px solid var(--accent);outline-offset:2px;border-radius:4px;}
body.desk *{text-transform:none !important;}
body.desk :is(h3,h4,h5,.gl,.count,.tag,.rs-go,.bm .n,.tape-lbl,small,label,.lbl,.kicker,.k){letter-spacing:normal !important;}
body.desk .hm .tile{border-radius:10px;overflow:hidden;}
body.desk .rt-axis{overflow:clip;overflow-clip-margin:16px;}
body.desk *{font-variant-numeric:normal !important;letter-spacing:normal;} body.desk :is(.v,.dk-q-big,.dk-deals .amt,.bm .v){letter-spacing:-0.01em;}

/* header + desk tabs */
.dk-top{background:var(--ink);color:#E4ECF5;display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:8px 28px;padding:10px 48px;min-height:56px;box-sizing:border-box;}
.dk-id{display:flex;align-items:center;gap:14px;flex-wrap:wrap;}
.dk-ed{font-size:13px;color:#BFD0E6;border-left:1px solid #2A4562;padding-left:14px;white-space:nowrap;}
.dk-askbtn{display:inline-flex;align-items:center;gap:8px;background:#1F5FC4;color:#fff !important;border-radius:999px;padding:8px 16px !important;font-weight:700 !important;text-decoration:none;min-height:36px;box-sizing:border-box;}
.dk-askbtn:hover{background:#174C9E;}
.dk-menu{display:none;font:inherit;font-size:14px;font-weight:700;color:#fff;background:transparent;border:1px solid #2A4562;border-radius:999px;padding:8px 16px;min-height:40px;cursor:pointer;}
.dk-unit{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;}
.dk-desks small{background:#F0F4F7;border-radius:999px;padding:1px 7px;}
.dk-brand{display:flex;align-items:center;gap:12px;color:#fff;text-decoration:none;font-size:24px;font-weight:800;letter-spacing:-.03em;}
.dk-mark{display:grid;grid-template-columns:repeat(3,8px);gap:3px;}
.dk-mark i{width:8px;height:8px;border-radius:50%;display:block;}
.dk-gnav{display:flex;flex-wrap:wrap;gap:4px 26px;font-size:15px;align-items:center;}
.dk-gnav a{color:#BFD0E6;text-decoration:none;padding:6px 0;font-weight:500;}
.dk-gnav a:hover{color:#fff;}
.dk-gnav a[aria-current]{color:#fff;font-weight:700;box-shadow:inset 0 -2px 0 #7FA9EC;}
.dk-acct{font-size:12px;color:#9FB2C8;border:1px solid #2A4562;border-radius:999px;padding:4px 10px;}
.dk-desks{display:flex;gap:0;overflow-x:auto;scrollbar-width:none;background:#fff;border-bottom:1px solid var(--line);padding:0 24px;position:sticky;top:0;z-index:60;box-shadow:0 1px 0 var(--line);}
.dk-desks::-webkit-scrollbar{display:none;}
.dk-desks a{display:flex;align-items:center;gap:7px;padding:14px 10px 11px;white-space:nowrap;text-decoration:none;font-size:14px;font-weight:600;color:var(--muted);border-bottom:3px solid transparent;}
.dk-desks a:hover{color:var(--ink);}
.dk-desks a[aria-current]{color:var(--ink);}
.dk-desks i{width:10px;height:10px;border-radius:50%;display:block;flex:0 0 auto;}
.dk-desks small{font-size:12px;color:var(--faint);font-weight:500;}

.dk-desks.ovf{-webkit-mask-image:linear-gradient(90deg,#000 88%,transparent);mask-image:linear-gradient(90deg,#000 88%,transparent);}
/* title band */
.dk-hero{background:var(--ink);color:#fff;}
.dk-hero-in{max-width:1344px;margin:0 auto;padding:36px 48px 40px;display:flex;flex-wrap:wrap;gap:28px 56px;align-items:flex-end;}
.dk-hero-main{flex:1 1 460px;min-width:0;}
.dk-crumb{font-size:13px;color:#9FB2C8;margin:0 0 14px;}
.dk-crumb a{color:#9FB2C8;text-decoration:none;} .dk-crumb a:hover{color:#fff;text-decoration:underline;}
.dk-eyebrow{font-size:16px;font-weight:600;color:#9CC0FF;margin:0 0 8px;}
.dk-hero h1{margin:0;font-size:clamp(44px,6.4vw,88px);line-height:.95;font-weight:900;letter-spacing:-.045em;color:#fff;max-width:16ch;}
.dk-topics{margin:16px 0 0;font-size:18px;color:#CFDCEA;max-width:60ch;line-height:1.45;}
.dk-hero .listen-bar{margin:22px 0 0 !important;padding:10px 14px !important;border:1px solid #2A4562 !important;border-radius:16px !important;background:#132C45 !important;color:#E4ECF5 !important;max-width:620px;}
.dk-hero .listen-bar div{color:#CFDCEA !important;} .dk-hero .listen-bar a{color:#9CC0FF !important;}
.dk-glance{flex:1 1 420px;display:grid;gap:22px;min-width:0;}
.dk-glance h2{margin:0 0 10px;font-size:15px;font-weight:700;color:#fff;}
.dk-stack{display:flex;gap:3px;border-radius:5px;overflow:hidden;height:18px;}
.dk-stack span{display:block;height:100%;}
.dk-leg{display:flex;flex-wrap:wrap;gap:6px 18px;margin-top:10px;font-size:14px;color:#DCE6F2;}
.dk-leg span{display:flex;align-items:center;gap:8px;} .dk-leg i{width:12px;height:12px;border-radius:3px;display:block;}
.dk-agency{display:grid;gap:8px;}
.dk-agency div{display:flex;align-items:center;gap:12px;font-size:15px;}
.dk-agency b{flex:0 0 120px;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.dk-agency .dots{display:flex;flex-wrap:wrap;gap:5px;} .dk-agency .dots i{width:14px;height:14px;border-radius:50%;background:#7FA9EC;display:block;}
.dk-agency em{font-style:normal;color:#CFDCEA;}

/* main column */
body.desk main#main{max-width:1344px;margin:0 auto;padding:28px 48px 56px;min-width:0;}
body.desk section{margin-bottom:44px;min-width:0;}
body.desk .section-head{border:0;padding:0;margin-bottom:12px;display:flex;align-items:baseline;gap:6px 14px;flex-wrap:wrap;}
body.desk h2{white-space:normal;overflow-wrap:break-word;min-width:0;max-width:100%;}
body.desk .section-head h2{font-size:30px;line-height:1.15;font-weight:800;letter-spacing:-.02em;color:var(--ink);margin:0;}
body.desk .section-head .count{font-size:15px;font-weight:500;color:var(--muted);}
body.desk .section-head .desc{font-size:15px;color:var(--muted);flex-basis:100%;}
.dk-kicker{display:none;}

/* watchlist chips */
.dk-watch{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 40px;}
.dk-watch .q{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ink);padding:8px 16px 8px 8px;border-radius:999px;background:#fff;box-shadow:0 0 0 1px var(--line);font-size:14px;min-height:44px;box-sizing:border-box;}
.dk-watch .q i{width:28px;height:28px;border-radius:50%;display:block;flex:0 0 auto;}
.dk-watch .q b{font-size:15px;font-weight:800;}
.dk-watch .q span{color:var(--muted);font-weight:600;}
.dk-watch a.q:hover{box-shadow:0 0 0 2px var(--accent);}
.dk-watch .lbl{align-self:center;font-size:14px;color:var(--muted);padding:0 6px;}

/* analysis + insights */
.dk-analysis{display:flex;flex-wrap:wrap;gap:28px 48px;margin-bottom:16px;}
.dk-analysis>section:first-child{flex:3 1 520px;} .dk-analysis>section:last-child{flex:2 1 340px;}
body.desk .pa-text{font-size:19px;line-height:1.65;color:var(--ink);margin:0;max-width:66ch;}
body.desk .pa-ins{display:grid;grid-template-columns:minmax(0,1fr);gap:12px;padding:0;margin:0;list-style:none;}
body.desk .pa-ins li{background:#fff;border:0;border-radius:16px;padding:20px 22px;font-size:15px;line-height:1.55;color:var(--muted);box-shadow:0 0 0 1px var(--line);}
body.desk .pa-ins li::before{content:none;}
body.desk .pa-ins li b{display:block;color:var(--ink);font-size:19px;font-weight:800;line-height:1.25;letter-spacing:-.01em;margin-bottom:8px;}

/* regulatory snapshot */
body.desk .rs .section-head a.rs-go{margin-left:auto;font-size:15px;font-weight:700;color:var(--accent);}
body.desk .rs-grid{grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;}
body.desk .rs-card{background:#fff;border:0;border-radius:16px;padding:16px 18px 8px;box-shadow:0 0 0 1px var(--line);}
body.desk .rs-card h3{font-size:16px;font-weight:800;color:var(--ink);}
body.desk .rs-card .t{font-size:14px;color:var(--ink);}

/* articles + papers */
.dk-lower{display:flex;flex-wrap:wrap;gap:28px 48px;}
.dk-lower>section:first-child{flex:3 1 520px;} .dk-lower>section:nth-child(2){flex:2 1 360px;}
.dk-filters{display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 8px;}
.dk-filters button{font:inherit;font-size:14px;font-weight:600;color:var(--muted);background:#fff;border:0;box-shadow:0 0 0 1px var(--line);padding:8px 14px;border-radius:999px;cursor:pointer;min-height:36px;}
.dk-filters button:hover{color:var(--ink);}
.dk-filters button[aria-pressed="true"]{background:var(--ink);color:#fff;box-shadow:none;}
.dk-filters .n{opacity:.7;margin-left:6px;}
body.desk .item{grid-template-columns:110px minmax(0,1fr);gap:4px 20px;padding:16px 0;border-top:1px solid var(--line);}
body.desk .item .when{font-size:14px;color:var(--muted);}
body.desk .item .headline{font-size:19px;font-weight:700;line-height:1.3;}
body.desk .item .headline a{color:var(--ink);}
body.desk .item .note{font-size:15px;line-height:1.55;color:var(--muted);}
body.desk .tag{border-radius:6px;font-size:12px;font-weight:700;padding:3px 8px;}
body.desk .seg button{min-height:36px;border-radius:999px;}
body.desk .seg button[aria-pressed="true"]{background:var(--ink);color:#fff;border-color:var(--ink);}
body.desk .pp-list li{padding:12px 0;border-top:1px solid var(--line);}
body.desk .pp-t{font-size:16px;font-weight:700;color:var(--ink);}

/* overview infographics */
.dk-panel{background:#fff;border-radius:22px;padding:10px 32px 22px;box-shadow:0 0 0 1px var(--line);}
.dk-deals{list-style:none;margin:0;padding:0;}
.dk-deals li{display:grid;gap:8px;padding:18px 0;border-top:1px solid var(--line);}
.dk-deals li:first-child{border-top:0;}
.dk-deals .row1{display:flex;flex-wrap:wrap;justify-content:space-between;gap:4px 16px;align-items:baseline;}
.dk-deals .row1 a{font-size:19px;font-weight:700;color:var(--ink);text-decoration:none;}
.dk-deals .row1 a:hover{text-decoration:underline;}
.dk-deals .row1 span{font-size:15px;color:var(--muted);}
.dk-deals .row2{display:flex;align-items:center;gap:14px;}
.dk-deals .bar{height:26px;border-radius:0 6px 6px 0;max-width:72%;min-width:6px;}
.dk-deals .amt{font-size:24px;font-weight:800;white-space:nowrap;}
.dk-legend{display:flex;flex-wrap:wrap;gap:8px 22px;font-size:14px;color:var(--muted);padding-top:12px;}
.dk-legend span{display:flex;align-items:center;gap:8px;} .dk-legend i{display:block;width:18px;height:12px;border-radius:3px;}
.dk-legend i.c{width:12px;height:12px;border-radius:50%;}
.dk-plate-row{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;padding:8px 0;border-top:1px solid var(--line);}
.dk-plate-row:first-child{border-top:0;}
.dk-plate-row>div:first-child{flex:0 0 160px;font-size:14px;color:var(--muted);}
.dk-wells{display:flex;flex-wrap:wrap;gap:8px;}
.dk-well{width:60px;height:60px;border-radius:50%;display:flex;flex-direction:column;align-items:center;justify-content:center;text-decoration:none;box-shadow:inset 0 0 0 1px rgba(14,34,54,.08);}
.dk-well b{font-size:12px;font-weight:700;} .dk-well span{font-size:11px;}
.dk-well:hover{box-shadow:0 0 0 3px var(--accent);}
.dk-sub{margin:6px 0 18px;font-size:16px;color:var(--muted);}
.dk-h2{margin:0;font-size:30px;font-weight:800;letter-spacing:-.02em;line-height:1.15;}
body.desk .bm{border-radius:14px;}
.dk-mv{position:relative;background:#EEF2F5;border-radius:4px;height:8px;margin-top:8px;}
.dk-mv::before{content:"";position:absolute;left:50%;top:-3px;width:1px;height:14px;background:#9AA8B5;}
.dk-mv i{position:absolute;top:0;height:8px;display:block;}

/* ---- polish pass: one card language, a type floor, aligned notes ---- */
body.desk .panel{border:0 !important;border-radius:18px;box-shadow:0 0 0 1px var(--line) !important;padding:22px 24px;background:#fff;}
body.desk .hero{align-items:start;}
body.desk .bench{background:transparent !important;border:0 !important;box-shadow:none !important;gap:10px !important;}
body.desk .bm{border-radius:14px;box-shadow:0 0 0 1px var(--line);padding:12px 14px;}
body.desk .bm:hover{box-shadow:0 0 0 2px var(--accent);}
body.desk .signal-card{border:0 !important;border-radius:16px !important;box-shadow:0 0 0 1px var(--line) !important;background:#fff;}
body.desk .signal-card:hover{box-shadow:0 0 0 2px var(--accent) !important;}
body.desk .rt-col{border:0 !important;border-radius:16px;background:#F0F4F7;}
body.desk .rt-card{border:0 !important;border-radius:12px;box-shadow:0 0 0 1px var(--line);}
body.desk :is(.kicker){display:block;font-size:14px !important;font-weight:700 !important;color:var(--accent-ink) !important;margin-bottom:6px;}
body.desk main h4,body.desk .panel h3{font-size:15px !important;font-weight:800 !important;color:var(--ink) !important;}
body.desk :is(.gl){font-size:13px !important;font-weight:700 !important;color:var(--muted) !important;}
body.desk :is(.src,.bench-note,.ms-asof,.cal-foot,.df-note,.pp-note,.rt-note,.pp-hint){font-size:13px !important;line-height:1.5;color:var(--muted);}
body.desk :is(.bench-note){text-align:left !important;margin-top:8px;}
body.desk :is(.ac,.rg,.pt,.who,.nx,.tick,.tm,.sep,.n,.d,.j,.dt,.c,.k){font-size:12px !important;}
body.desk .rt-axis .tick{font-size:12px !important;}
body.desk .bm .n{font-size:13px !important;font-weight:700;color:var(--muted);}
body.desk .bm .v{font-size:22px !important;}
body.desk .bm :is(.up,.dn,.w){font-size:13px !important;}
body.desk .section-head .desc,body.desk .section-head span.desc{text-align:left !important;margin:0 !important;flex-basis:100%;}
body.desk .seg button,body.desk .hm-head .seg button,body.desk .df-top button{font-size:13px !important;min-height:34px;padding:6px 14px;}
body.desk .tag{font-size:12px !important;}
body.desk .why{font-size:13px !important;}

/* in-site quote panel */
.dk-q{position:fixed;inset:0;background:rgba(14,34,54,.55);display:flex;align-items:center;justify-content:center;padding:16px;z-index:1000;}
.dk-q[hidden]{display:none;}
.dk-q-box{position:relative;background:#fff;border-radius:20px;padding:28px 28px 24px;max-width:440px;width:100%;box-shadow:0 20px 60px rgba(14,34,54,.35);}
.dk-q-box h2{margin:0 40px 12px 0;font-size:26px;font-weight:800;letter-spacing:-.02em;}
.dk-q-x{position:absolute;top:14px;right:14px;width:44px;height:44px;border-radius:50%;border:0;background:#F0F4F7;font-size:24px;cursor:pointer;color:var(--ink);}
.dk-q-big{margin:0;font-size:34px;font-weight:800;}
.dk-q-chg{margin:4px 0 0;font-size:17px;font-weight:600;}
.dk-q-note{margin:6px 0 0;font-size:14px;color:var(--muted);}
.dk-q-msg{margin:18px 0 0;padding-top:14px;border-top:1px solid var(--line);font-size:15px;line-height:1.5;color:var(--muted);}
/* the chart popup no longer links out */
body.desk .scm-panel a[href*="finance.yahoo.com"]{display:none;}

/* sources + footer */
.dk-sources{border-top:1px solid var(--line);padding-top:12px;margin-top:8px;}
.dk-sources summary{font-size:15px;color:var(--muted);cursor:pointer;font-weight:600;min-height:32px;}
.dk-sources .dk-src-body{font-size:14px;color:var(--muted);line-height:1.6;margin-top:8px;}
.dk-sources .dk-src-body p{margin:0 0 8px;}
body.desk footer{max-width:1344px;margin:0 auto;border-top:1px solid var(--line);padding:16px 48px;font-size:13px;color:var(--faint);}
body.desk .site-foot{max-width:1344px;margin:0 auto;padding:12px 48px 28px;}

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

@media (max-width:760px){
  .dk-top{padding:8px 16px;}
  .dk-ed{display:none;}
  .dk-lblx{display:none;}
  .dk-menu{display:inline-block;}
  .dk-gnav{display:none;flex-basis:100%;flex-direction:column;align-items:stretch;gap:0;padding:4px 0 8px;}
  .dk-top.open .dk-gnav{display:flex;}
  .dk-gnav a{padding:12px 0;border-top:1px solid #1C3550;}
  .dk-gnav .dk-askbtn{margin-top:8px;justify-content:center;}
  .dk-desks{padding:0 8px;}

  .dk-hero-in{padding:24px 16px 28px;}
  body.desk main#main{padding:20px 16px 40px;}
  body.desk footer,body.desk .site-foot{padding-inline:16px;}
  body.desk .item{grid-template-columns:1fr;}
  .dk-panel{padding:6px 16px 16px;border-radius:16px;}
  .dk-plate-row>div:first-child{flex-basis:100%;}
  .dk-well{width:52px;height:52px;}
  .dk-deals .bar{max-width:58%;}
}
@media (prefers-reduced-motion:reduce){body.desk *{scroll-behavior:auto !important;}}
</style>
"""

DESK_JS = r"""<script>
/* Direction D: watchlist chips, overview well plate + tile move bars, agency dots, filters, tracker link */
(function(){
  var cfg=%(cfg)s;
  var esc=function(t){return String(t).replace(/[&<>"]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c];});};
  var yf=function(s){return "https://finance.yahoo.com/quote/"+encodeURIComponent(s.replace(".B","-B"))+"/";};
  var pct=function(v){return (v>=0?"+":"−")+Math.abs(v).toFixed(1)+"%%";};
  function well(v){var a=Math.abs(v);
    if(v==null||isNaN(v)) return ["#E3E8ED","#0E2236"];
    if(a<1) return ["#E3E8ED","#0E2236"];
    if(v>0) return a<3?["#D3EEDD","#0E2236"]:a<6?["#7CC79A","#0E2236"]:["#1E7A4C","#FFFFFF"];
    return a<3?["#F8DCC4","#0E2236"]:a<6?["#EDA56A","#0E2236"]:["#B4560F","#FFFFFF"];}
  var T=window.HH_TAPES||{};

  /* desks: site-wide tape stays on market movers */
  var mv=document.getElementById("tape-movers"),cm=document.querySelector(".tape.cm"),bio=document.querySelector(".tape.bio");
  function tapes(){var c=cfg.page_tape==="cm"; if(mv)mv.hidden=c; if(cm)cm.hidden=!c; if(bio)bio.hidden=true;}
  if(cfg.desk){tapes(); setTimeout(tapes,0);}


  /* header: phone menu, Ask the Pulse, current desk tab in view, one-line ticker labels */
  var topb=document.querySelector(".dk-top"), mb=topb&&topb.querySelector(".dk-menu");
  if(mb){ mb.addEventListener("click",function(){var o=topb.classList.toggle("open"); mb.setAttribute("aria-expanded",o?"true":"false");}); }
  var ab=document.querySelector("[data-ask]");
  if(ab){ ab.addEventListener("click",function(e){var f=document.getElementById("ask-fab"); if(f&&!f.hidden){e.preventDefault(); f.click();}}); }
  var dt=document.querySelector(".dk-desks"), cur=dt&&dt.querySelector("[aria-current]");
  function ovf(){ if(!dt) return; var o=dt.scrollWidth>dt.clientWidth+2 && dt.scrollLeft+dt.clientWidth<dt.scrollWidth-4; dt.classList.toggle("ovf",o); }
  if(dt){ dt.addEventListener("scroll",ovf,{passive:true}); window.addEventListener("resize",ovf); }
  if(cur&&dt.scrollWidth>dt.clientWidth){ dt.scrollLeft=Math.max(0,cur.offsetLeft-(dt.clientWidth-cur.offsetWidth)/2); }
  ovf();
  [].forEach.call(document.querySelectorAll(".tape-lbl"),function(l){ if(!/7-day/.test(l.textContent)) l.innerHTML=l.textContent.trim()+'<span class="dk-lblx">, 7-day change</span>'; });

  /* watchlist chips */
  var w=document.getElementById("dk-watch");
  if(w){
    var rows=[];
    if(cfg.watch_tape&&T[cfg.watch_tape]){
      rows=T[cfg.watch_tape].map(function(d){return cfg.watch_tape==="cm"?{s:d[0],p:d[1],c:d[2],u:"https://tradingeconomics.com/commodity/"+d[3]}:{s:d[0],p:d[1],c:d[2]};});
    } else {
      var all={}; Object.keys(T).forEach(function(k){(T[k]||[]).forEach(function(d){if(typeof d[1]==="number"&&!all[d[0]])all[d[0]]=d;});});
      rows=cfg.watch.map(function(x){var d=all[x[0]];return {s:x[0],n:x[1],p:d?d[1]:null,c:d?d[2]:null};});
    }
    w.innerHTML=rows.map(function(r){
      var f=well(r.c), val=r.c!=null?pct(r.c)+" 7d":esc(r.n||"")+", quote";
      return '<a class="q" href="'+(r.u||yf(r.s))+'" target="_blank" rel="noopener" title="'+esc(r.s)+(r.u?' on Trading Economics':' on Yahoo Finance')+'"><i aria-hidden="true" style="background:'+f[0]+'"></i><b>'+esc(r.s)+'</b><span>'+val+'</span></a>';
    }).join("");
  }

  /* overview well plate */
  var pl=document.getElementById("dk-plate");
  if(pl&&T.bio){
    var V={}; T.bio.forEach(function(d){V[d[0]]=d[2];});
    var h=cfg.plate.map(function(g){
      var ws=g[1].filter(function(s){return V[s]!=null;}).map(function(s){var f=well(V[s]);
        return '<a class="dk-well" href="'+yf(s)+'" target="_blank" rel="noopener" title="'+s+' '+pct(V[s])+' over 7 days" style="background:'+f[0]+';color:'+f[1]+'"><b>'+s+'</b><span>'+pct(V[s])+'</span></a>';}).join("");
      return ws?'<div class="dk-plate-row"><div>'+esc(g[0])+'</div><div class="dk-wells">'+ws+'</div></div>':"";
    }).join("");
    if(h){pl.querySelector(".dk-plate-body").innerHTML=h; pl.hidden=false;}
  }


  /* sector heatmap: same green/orange steps as the well plate, kept on redraw */
  var hm=document.getElementById("hm");
  function recolor(){
    if(!hm) return;
    [].forEach.call(hm.querySelectorAll(".tile"),function(t){
      var c=t.querySelector(".c"), tb=t.querySelector(".tb"); if(!c||!tb) return;
      var m=/([+\u2212-])\s*([\d.]+)/.exec(c.textContent); if(!m) return;
      var v=parseFloat(m[2])*(m[1]==="+"?1:-1), f=well(v);
      tb.style.background=f[0]; [].forEach.call(t.querySelectorAll(".t,.c"),function(x){x.style.color=f[1];});
    });
    [["lg-dn",-7],["lg-0",0],["lg-up",7]].forEach(function(x){var e=document.getElementById(x[0]); if(e) e.style.background=well(x[1])[0];});
  }
  if(hm){ recolor(); new MutationObserver(recolor).observe(hm,{childList:true}); }

  /* overview tiles: seven-day move bar */
  function bars(){
    [].forEach.call(document.querySelectorAll(".bm"),function(a){
      if(a.querySelector(".dk-mv")) return;
      var t=(a.querySelector(".w")||{}).textContent||""; var m=/([+−-])\s*([\d.,]+)\s*(%%|bp)/.exec(t); if(!m) return;
      var v=parseFloat(m[2].replace(",",""))*(m[1]==="+"?1:-1), sc=m[3]==="bp"?20:15, wd=Math.min(Math.abs(v)/sc*50,50);
      var bar=document.createElement("div"); bar.className="dk-mv"; bar.setAttribute("aria-hidden","true");
      bar.innerHTML='<i style="'+(v>=0?'left:50%%;border-radius:0 3px 3px 0;background:#1E7A4C':'right:50%%;border-radius:3px 0 0 3px;background:#B4560F')+';width:'+wd.toFixed(1)+'%%"></i>';
      a.appendChild(bar);
    });
  }
  bars(); setTimeout(bars,300);

  /* desk: regulatory actions by agency (from the rendered snapshot) */
  var ag=document.getElementById("dk-agency");
  function agency(){
    if(!ag) return;
    var cards=[].slice.call(document.querySelectorAll(".rs-card"));
    if(!cards.length){ag.parentNode.hidden=true;return;}
    var tot=0, h=cards.map(function(c){var n=c.querySelectorAll("li").length; tot+=n;
      var name=((c.querySelector("h3")||{}).innerText||"").split("\n")[0].trim();
      var dots=""; for(var i=0;i<Math.min(n,24);i++) dots+="<i></i>";
      return '<div><b>'+esc(name)+'</b><span class="dots" aria-hidden="true">'+dots+'</span><em>'+n+'</em></div>';}).join("");
    ag.innerHTML=h; var t=document.getElementById("dk-agency-t"); if(t) t.textContent=tot+" regulatory action"+(tot===1?"":"s")+" by agency";
  }
  setTimeout(agency,50);


  /* every stock, index, commodity and currency stays on the site:
     names with chart data open the candlestick chart (the edition's own handler);
     anything else opens this panel with the latest figures from the page */
  var QSEL='a[href*="finance.yahoo.com/quote/"],a[href*="tradingeconomics.com/"]';
  var dlg=null;
  function closeQ(){ if(dlg){ dlg.hidden=true; if(dlg._from) dlg._from.focus(); } }
  function openQ(a){
    var href=a.getAttribute("href")||"", sym="";
    var m=/quote\/([^\/?#]+)/.exec(href); if(m) sym=decodeURIComponent(m[1]);
    var tm=/tradingeconomics\.com\/(?:commodity\/)?([^\/?#]+)/.exec(href);
    var lines=(a.innerText||"").split(/\n+/).map(function(x){return x.trim();}).filter(Boolean);
    var name=(a.getAttribute("title")||"").replace(/ on (Yahoo Finance|Trading Economics)$/,"").trim()||lines[0]||sym;
    var row=null, asof="";
    Object.keys(T).forEach(function(k){(T[k]||[]).forEach(function(d){
      if(row) return;
      if((sym&&(d[0]===sym||d[3]===sym||String(d[0]).replace(/\./g,"-")===sym))||(tm&&d[3]===tm[1])||d[0]===name){row=d; var lb=document.querySelector("#"+(k==="top"?"tape":k)+"-track .tk.asof .s"); asof=lb?lb.textContent:"";}
    });});
    if(!dlg){
      dlg=document.createElement("div"); dlg.className="dk-q"; dlg.hidden=true;
      dlg.innerHTML='<div class="dk-q-box" role="dialog" aria-modal="true" aria-labelledby="dk-q-h"><button type="button" class="dk-q-x" aria-label="Close">×</button><h2 id="dk-q-h"></h2><div class="dk-q-body"></div></div>';
      document.body.appendChild(dlg);
      dlg.addEventListener("click",function(e){ if(e.target===dlg||e.target.closest(".dk-q-x")) closeQ(); });
      document.addEventListener("keydown",function(e){ if(e.key==="Escape"&&dlg&&!dlg.hidden) closeQ(); });
    }
    var body="";
    if(row&&typeof row[1]==="number"){
      var unit=(row[5]&&typeof row[5]==="string")?" "+row[5]:"";
      body+='<p class="dk-q-big">'+row[1].toLocaleString("en-US",{maximumFractionDigits:4})+esc(unit)+'</p>';
      if(typeof row[2]==="number") body+='<p class="dk-q-chg" style="color:'+(row[2]>=0?"#1E7A4C":"#B4560F")+'">'+pct(row[2])+' over 7 days</p>';
      if(asof) body+='<p class="dk-q-note">'+esc(asof)+'</p>';
    } else if(lines.length>1){
      body+='<p class="dk-q-big">'+esc(lines[1])+'</p>'+(lines.length>2?'<p class="dk-q-chg">'+esc(lines.slice(2).join(", "))+'</p>':'');
    }
    body+='<p class="dk-q-msg">A candlestick chart for '+esc(name)+' isn’t in today’s data yet. It will open here once the daily update adds its price history.</p>';
    dlg.querySelector("#dk-q-h").textContent=name;
    dlg.querySelector(".dk-q-body").innerHTML=body;
    dlg._from=a; dlg.hidden=false; dlg.querySelector(".dk-q-x").focus();
  }
  document.addEventListener("click",function(e){
    var a=e.target.closest&&e.target.closest(QSEL); if(!a) return;
    if(a.closest(".scm-panel")){ e.preventDefault(); return; }
    if(e.defaultPrevented) return;          /* the candlestick chart already opened */
    e.preventDefault(); openQ(a);
  });
  /* quote links no longer open new tabs */
  function local(){ [].forEach.call(document.querySelectorAll(QSEL),function(a){a.removeAttribute("target");}); }
  local(); setTimeout(local,400);
  /* wording that pointed people off the site */
  [].forEach.call(document.querySelectorAll("p,span,div,small"),function(el){
    if(el.children.length) return;
    var t=el.textContent;
    if(/Yahoo Finance quote|tile for Yahoo Finance/.test(t)) el.textContent=t.replace("for its Yahoo Finance quote","for its chart").replace("tap any tile for Yahoo Finance","tap any tile for its chart");
  });


  /* Deal Flow: open on the past 7 days when the last 24 hours had no deals */
  setTimeout(function(){
    var tot=document.getElementById("df-total"), b7=document.querySelector('.df-top button[data-w="7d"]');
    if(tot&&b7&&tot.textContent.trim()==="0"&&b7.getAttribute("aria-pressed")!=="true") b7.click();
  },60);

  /* article type filters */
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

  /* regulatory snapshot: link into the full tracker, filtered to this desk */
  var rs=document.querySelector(".rs[data-reg]");
  if(rs&&cfg.desk){ setTimeout(function(){
    var head=rs.querySelector(".section-head"); if(!head) return;
    var old=head.querySelector(".rs-go"), a=document.createElement("a");
    a.className="rs-go"; a.href=cfg.tracker; a.textContent="Open the full tracker";
    if(old) old.replaceWith(a); else head.appendChild(a);
  },0); }
  var ppl=document.querySelector(".pp-list"); if(ppl) ppl.setAttribute("aria-live","polite");
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



def _money(t):
    best = 0.0
    for m in re.finditer(r"\$\s?([\d.,]+)\s*(B|M|bn|billion|million)\b", t):
        v = float(m.group(1).replace(",", ""))
        best = max(best, v * 1000 if m.group(2) in ("B", "bn", "billion") else v)
    return best


def _fmt_money(m):
    return f"${m/1000:.1f}B".replace(".0B", "B") if m >= 1000 else f"${m:.0f}M"


def _deals(panel):
    """Deals with a headline value from the edition's Today's Signals cards."""
    out = []
    for c in re.findall(r'<div class="signal-card[^"]*">(.*?)\n\s*</div>\s*(?=<div class="signal-card|</div>)', panel, re.S):
        tag = re.search(r'class="tag[^"]*">([^<]+)', c)
        tag = html.unescape(tag.group(1)).strip() if tag else ""
        if tag not in ("M&A", "Licensing", "Acquisition", "Deal"):
            continue
        hl = re.search(r'class="headline">(.*?)</div>', c, re.S)
        link = re.search(r'href="([^"]+)"', hl.group(1)) if hl else None
        head = html.unescape(re.sub(r"<[^>]+>", "", hl.group(1))).strip() if hl else ""
        val = re.search(r'class="value">(.*?)</div>', c, re.S)
        val = html.unescape(re.sub(r"<[^>]+>", "", val.group(1))).strip() if val else ""
        src = re.search(r'class="src">(.*?)</div>', c, re.S)
        src = html.unescape(re.sub(r"<[^>]+>", "", src.group(1))).strip() if src else ""
        amt = _money(val) or _money(head)
        if amt:
            out.append({"tag": tag, "head": head, "val": val, "src": src, "amt": amt, "url": link.group(1) if link else "#"})
    out.sort(key=lambda d: -d["amt"])
    return out


def _deal_block(deals):
    mx = deals[0]["amt"]
    rows = []
    for d in deals:
        acq = d["tag"] != "Licensing"
        w = max(d["amt"] / mx * 100, 2)
        rows.append(
            f'<li><div class="row1"><a href="{html.escape(d["url"])}" target="_blank" rel="noopener">{html.escape(d["head"])}</a>'
            f'<span>{html.escape(d["tag"])}, {html.escape(d["src"])}</span></div>'
            f'<div class="row2"><div class="bar" style="width:{w:.1f}%;background:{"#1F5FC4" if acq else "#7FA9EC"}"></div>'
            f'<span class="amt">{html.escape(d["val"] if len(d["val"]) < 26 else ("up to " if not acq else "") + _fmt_money(d["amt"]))}</span></div></li>')
    return ('<section aria-labelledby="dk-deals-h"><h2 class="dk-h2" id="dk-deals-h">Deal flow in this edition</h2>'
            '<p class="dk-sub">M&amp;A and licensing with a disclosed value, sized by headline value. Licensing figures are "up to" totals including milestones.</p>'
            f'<div class="dk-panel"><ul class="dk-deals">{"".join(rows)}</ul>'
            '<div class="dk-legend"><span><i style="background:#1F5FC4"></i>Acquisition or bid</span><span><i style="background:#7FA9EC"></i>Licensing</span></div></div></section>\n')


def _plate_block():
    leg = "".join(f'<span><i class="c" style="background:{c}"></i>{t}</span>' for c, t in
                  [("#B4560F", "down 6% or more"), ("#EDA56A", "down 3–6%"), ("#E3E8ED", "within 1%"), ("#7CC79A", "up 3–6%"), ("#1E7A4C", "up 6% or more")])
    return ('<section id="dk-plate" aria-labelledby="dk-plate-h" hidden><h2 class="dk-h2" id="dk-plate-h">The week in biotech stocks</h2>'
            '<p class="dk-sub">Each circle is one stock we track, colored by its seven-day move. Tap one for its quote.</p>'
            f'<div class="dk-panel"><div class="dk-plate-body"></div><div class="dk-legend" style="border-top:1px solid var(--line)">{leg}</div></div></section>\n')


def _glance(arts):
    labels = [html.unescape(l).strip() for l in re.findall(r'<span class="tag [a-z]+">([^<]+)</span>', arts)]
    if not labels:
        return ""
    counts = []
    for name, col, members in ART_GROUPS:
        if members is None:
            continue
        counts.append([name, col, sum(1 for l in labels if l in members)])
    known = set().union(*[m for _, _, m in ART_GROUPS if m])
    counts.insert(1, [ART_GROUPS[1][0], ART_GROUPS[1][1], sum(1 for l in labels if l not in known)])
    counts = [c for c in counts if c[2]]
    stack = "".join(f'<span style="flex:{n} 1 0;background:{col}" title="{html.escape(nm)}: {n}"></span>' for nm, col, n in counts)
    leg = "".join(f'<span><i style="background:{col}"></i>{html.escape(nm)} <b>{n}</b></span>' for nm, col, n in counts)
    aria = ", ".join(f"{nm} {n}" for nm, _, n in counts)
    return (f'<div class="dk-glance"><div><h2>{len(labels)} article{"s" if len(labels) != 1 else ""} in this edition</h2>'
            f'<div class="dk-stack" role="img" aria-label="{html.escape(aria)}">{stack}</div><div class="dk-leg">{leg}</div></div>'
            '<div><h2 id="dk-agency-t">Regulatory actions by agency</h2><div class="dk-agency" id="dk-agency"></div></div></div>')


def apply_layout(doc, pid, slug, label, counts, date_label, edition_no, preview):
    """Direction D look for one built page: a full desk for panels in DESKS,
    the shared frame (header, desk tabs, title band) for every other page."""
    import json
    is_desk = pid in DESKS
    cfg = DESKS.get(pid)
    shell = SHELL.get(slug)
    if not is_desk and shell is None:
        return doc
    doc = re.sub(r"<body(?![^>]*class=)", '<body class="desk"', doc, count=1)
    doc, listen = _cut(doc, r'\s*<section class="listen-bar".*?</section>')
    gnav = [("", "Overview"), ("daily-pulse", "Daily Pulse"), ("deep-dive", "Deep Dive"), ("about", "About")]
    def is_cur(s):
        return (not is_desk) and s == slug
    links = "".join(f'<a href="{_href(s, preview)}"{" aria-current=\"page\"" if is_cur(s) else ""}>{html.escape(l)}</a>' for s, l in gnav)
    dm = re.search(r"([A-Z][a-z]+) (\d+), \d{4}", date_label or "")
    short = f"{dm.group(1)[:3]} {dm.group(2)}" if dm else ""
    ed = (f'<span class="dk-ed">Edition {edition_no}' + (f", {short}" if short else "") + '</span>') if edition_no else ""
    ask = (f'<a class="dk-askbtn" href="{_href("deep-dive", preview)}" data-ask>'
           '<svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16"><circle cx="7" cy="7" r="5" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M11 11l3.5 3.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>Ask the Pulse</a>')
    mark = "".join(f'<i style="background:{c}"></i>' for c in ("#1F5FC4", "#7CC79A", "#3A5470", "#EDA56A", "#1E7A4C", "#CFE0FA"))
    top = (f'<header class="dk-top"><div class="dk-id"><a class="dk-brand" href="{_href("", preview)}"><span class="dk-mark" aria-hidden="true">{mark}</span>BioMarket Pulse</a>{ed}'
           + ('<span class="dk-acct">Sandbox</span>' if preview else "") + '</div>'
           '<button type="button" class="dk-menu" aria-expanded="false" aria-controls="dk-gnav">Menu</button>'
           f'<nav class="dk-gnav" id="dk-gnav" aria-label="Site">{links}{ask}</nav></header>\n')
    tabs = []
    for dslug, dpid, dl in DESK_NAV:
        n = counts.get(dpid)
        cur = dpid == pid or (not is_desk and dslug == slug)
        col = DESK_COLOR.get(dpid, "#4A5B6C")
        tabs.append(f'<a href="{_href(dslug, preview)}"' + (f' aria-current="page" style="border-bottom-color:{col}"' if cur else "") +
                    f'><i aria-hidden="true" style="background:{col}"></i>{html.escape(dl)}' + (f' <small title="{n} articles in this edition">{n}<span class="dk-unit"> articles</span></small>' if n else "") + '</a>')
    tabs = '<nav class="dk-desks" aria-label="Research desks">' + "".join(tabs) + '</nav>\n'
    doc = re.sub(r'<header class="masthead">.*?</header>', lambda m: top + tabs, doc, count=1, flags=re.S)
    doc = re.sub(r'\s*<nav class="tabs" id="tabs".*?</nav>\s*<script>\(function\(\)\{var c=document\.querySelector\(\'\.tabs.*?</script>',
                 "", doc, count=1, flags=re.S)
    doc, src = _cut(doc, r'\s*<div class="sources">.*?</div>(?=\s*<div>)')
    m = re.search(r'<main id="main">(.*?)</main>', doc, re.S)
    if not m:
        return doc
    panel = m.group(1)

    if is_desk:
        kind, title, sub = cfg["kind"], label, " · ".join(html.escape(t) for t in cfg["topics"])
    else:
        kind, title, sub = shell[0], shell[1], html.escape(shell[2])
    eyebrow = ", ".join(x for x in (kind, f"edition {edition_no}" if edition_no else "", date_label) if x)
    crumb = (f'<nav class="dk-crumb" aria-label="Breadcrumb"><a href="{_href("", preview)}">BioMarket Pulse</a> / '
             + ("Research desks / " if is_desk else "") + f'<span aria-current="page">{html.escape(title)}</span></nav>')

    deals = _deals(panel) if slug == "" else []
    h1 = title
    if slug == "" and len(deals) >= 2:
        total = sum(d["amt"] for d in deals)
        h1 = f"{len(deals)} deals, {_fmt_money(total)} in headline value"
        sub = html.escape("Market overview: deal flow, how the biotech stocks we track moved, markets and today's signals.")

    secs = _top_sections(panel) if is_desk else []
    arts = next((s for s in secs if "<h2>Latest Articles</h2>" in s), "")
    glance = _glance(arts) if is_desk else ""
    hero = (f'<div class="dk-hero"><div class="dk-hero-in"><div class="dk-hero-main">'
            f'<p class="dk-eyebrow">{html.escape(eyebrow)}</p><h1>{html.escape(h1)}</h1>'
            + (f'<p class="dk-topics">{sub}</p>' if sub else "") + listen.strip() + f'</div>{glance}</div></div>\n')

    sources = ""
    if src:
        body = re.sub(r'^\s*<div class="sources">|</div>\s*$', "", src.strip())
        sources = ('<details class="dk-sources"><summary>Sources and methodology, refreshed with each edition</summary>'
                   f'<div class="dk-src-body"><p>{body}</p>'
                   f'<p>Compiled each morning as part of edition {edition_no}. Every article, regulatory action and paper links to its original source. '
                   f'See <a href="{_href("about", preview)}">About and methodology</a>.</p></div></details>\n')

    if is_desk:
        pa = next((s for s in secs if s.startswith('<section class="pa"')), "")
        rs = next((s for s in secs if 'class="rs"' in s[:40]), "")
        pp = next((s for s in secs if s.startswith('<section class="pp-sec"')), "")
        ai = secs.index(arts) if arts else len(secs)
        early = [s for i, s in enumerate(secs) if s not in (pa, rs, pp, arts) and i < ai]
        late = [s for i, s in enumerate(secs) if s not in (pa, rs, pp, arts) and i > ai]
        watch = (f'<div class="dk-watch" id="dk-watch" aria-label="{html.escape(label)} watchlist"></div>\n'
                 if (cfg["watch"] or cfg["watch_tape"]) else "")
        content = (watch + _analysis(pa) + rs + "\n" + "\n".join(early) +
                   '<div class="dk-lower">\n' + _filters(arts) + "\n" + pp + "\n</div>\n" + "\n".join(late))
    else:
        content = panel
        if slug == "":
            content = (_deal_block(deals) if len(deals) >= 2 else "") + _plate_block() + content
    new_main = '\n<main id="main">\n' + content + sources + "</main>\n"
    doc = doc[:m.start()] + hero + new_main + doc[m.end():]

    js_cfg = {"watch": cfg["watch"] if is_desk else [], "watch_tape": cfg["watch_tape"] if is_desk else None,
              "page_tape": cfg.get("page_tape") if is_desk else None,
              "desk": is_desk, "plate": PLATE_GROUPS if slug == "" else [],
              "tracker": _href("regulatory", preview) + "?sector=" + REG_KEY.get(pid, "")}
    # security: Ask answers and deal-flow text escape quotes too, so a link or title can't break out of its attribute
    doc = doc.replace("""function esc(t){return String(t).replace(/[&<>]/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;"}[c];});}""",
                      """function esc(t){return String(t).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];});}""")
    doc = doc.replace(""".replace(/&(?!(gt|lt|amp);)/g,"&amp;").replace(/</g,"&lt;");};""",
                      """.replace(/&(?!(gt|lt|amp|quot);)/g,"&amp;").replace(/</g,"&lt;").replace(/"/g,"&quot;");};""")
    doc = doc.replace("(lr.year?' '+lr.year:'')", "(lr.year?' '+(parseInt(lr.year,10)||''):'')")
    # one typeface: the legacy monospace numerals become Schibsted figures
    doc = re.sub(r"'IBM Plex Mono',\s*monospace", "'Schibsted Grotesk',system-ui,sans-serif", doc)
    doc = doc.replace("</head>", FONT_LINK + DESK_CSS + "</head>", 1)
    doc = doc.replace("</body>", DESK_JS % {"cfg": json.dumps(js_cfg)} + "</body>", 1)
    return doc


def apply_tracker_link(doc):
    return doc.replace("</body>", TRACKER_JS + "</body>", 1)


apply_desk_layout = apply_layout  # backwards name
