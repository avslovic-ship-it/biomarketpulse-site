"""Build /partnering/ (pharma) and /partnering/agriculture/ from the sandbox partner-finder pages.
The Ask bar needs Claude, so it is hidden on the public site."""
import os
HERE=os.path.dirname(os.path.abspath(__file__));ROOT=os.path.dirname(HERE)
NAV=[("/","Overview"),("/daily-pulse/","Daily Pulse"),("/deep-dive/","Deep Dive"),("/partnering/","Partnering (beta)"),("/about/","About")]
PAGES={
 "pharma":dict(src="pharma.html",out="partnering",sub="Cyclic peptides in pharma",
  meta="Trials, papers, deals and approvals to Nov 21, 2026 · latest quarterly results · prices to Nov 20",
  title="Partnering (beta): Cyclic Peptides in Pharma · BioMarket Pulse",
  desc="Which large pharma companies buy cyclic peptides, and which have the money but no position yet: deals, pipeline, trials and finances."),
 "agriculture":dict(src="agriculture.html",out="partnering/agriculture",sub="Fungicidal peptides in Brazil",
  meta="Registry to Jan 13, 2026 · company results and news Oct 1 – Nov 17, 2026 · prices to mid-November",
  title="Partnering (beta): Fungicidal Peptides in Brazil · BioMarket Pulse",
  desc="Which crop-protection companies need new fungicide modes of action in Brazil, which can reach the acres, and which can afford a deal."),
}
CSS=(".snav{display:flex;flex-wrap:wrap;gap:4px 20px;font-size:15px}.snav a{color:var(--mut);text-decoration:none;padding:6px 0;font-weight:500}"
 ".snav a:hover{color:var(--ink)}.snav a[aria-current]{color:var(--ink);font-weight:700;box-shadow:inset 0 -2px 0 var(--blue)}"
 ".seg{display:inline-flex;gap:4px;padding:4px;border-radius:999px;background:var(--card);box-shadow:0 0 0 1px var(--line);margin-top:4px}"
 ".seg a{font-size:15px;font-weight:700;text-decoration:none;color:var(--ink);min-height:40px;display:inline-flex;align-items:center;padding:0 20px;border-radius:999px}"
 ".seg a:hover{background:var(--soft)}.seg a[aria-current]{background:var(--ink);color:var(--bg)}"
 ".segbar{padding-top:18px}")
def build():
    for key,p in PAGES.items():
        s=open(os.path.join(HERE,"partnering_src",p["src"]),encoding="utf-8").read()
        a='<section class="ask" aria-label="Ask the Pulse">';assert a in s
        s=s.replace(a,'<section class="ask" aria-label="Ask the Pulse" hidden style="display:none">')
        i=s.index('<header class="top">');j=s.index('</header>',i)+9
        nav="".join(f'<a href="{h}"{" aria-current=\"page\"" if h=="/partnering/" else ""}>{l}</a>' for h,l in NAV)
        seg="".join(f'<a href="{h}"{" aria-current=\"page\"" if k==key else ""}>{l}</a>' for k,h,l in [("pharma","/partnering/","Pharma"),("agriculture","/partnering/agriculture/","Agriculture")])
        hdr=(f'<header class="top"><div class="wrap">\n <div><a class="brand" href="/" style="color:inherit;text-decoration:none">BioMarket Pulse <span>· Partnering (beta): {p["sub"]}</span></a>\n'
             f' <div class="meta">{p["meta"]} <span class="sandbox">Beta</span></div></div>\n <nav class="snav" aria-label="Site">{nav}</nav>\n</div></header>\n'
             f'<div class="wrap segbar"><nav class="seg" aria-label="Partnering sector">{seg}</nav></div>')
        s=s[:i]+hdr+s[j:]
        assert ":root{color-scheme:light dark;" in s
        s=s.replace(":root{color-scheme:light dark;",":root{color-scheme:light;",1)  # always light, like the rest of the site
        s=s.replace("</style>",CSS+"</style>",1)
        t0=s.index("<title>");t1=s.index("</title>")+8
        s=s[:t0]+f'<title>{p["title"]}</title>\n<meta name="description" content="{p["desc"]}">\n<link rel="icon" href="/favicon.svg" type="image/svg+xml">'+s[t1:]
        f0=s.index("<footer>");f1=s.index("</footer>")+9
        s=s[:f0]+(f'<footer><div class="wrap">BioMarket Pulse · Partnering (beta): {p["sub"].lower()} · Prepared November 21, 2026 · '
                  'For information only, not investment advice · <a href="/about/" style="color:inherit">About &amp; methodology</a></div></footer>')+s[f1:]
        s=s.replace("Built for a business-development lead at a cyclic-peptide company.","For business-development teams at cyclic-peptide companies.")
        s=s.replace("Built for a business-development lead selling fungicidal peptides.","For business-development teams at biopesticide companies selling fungicidal peptides.")
        os.makedirs(os.path.join(ROOT,p["out"]),exist_ok=True)
        open(os.path.join(ROOT,p["out"],"index.html"),"w",encoding="utf-8").write(s)
        print("wrote",p["out"])
if __name__=="__main__":build()
