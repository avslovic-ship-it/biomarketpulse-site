#!/usr/bin/env python3
"""Nightly patent feed for BioMarket Pulse.

Asks EPO Open Patent Services (OPS) for the newest published patent documents in each Pulse
section and writes data/patents.json. Needs two repository secrets: EPO_OPS_KEY and EPO_OPS_SECRET
(free registration at developers.epo.org). Without them it exits quietly and changes nothing.

Output: {"generated": ISO time, "window": {"from","to"}, "tabs": {section: [patent, ...]}}
patent = {"t": title, "a": applicant, "n": "EP4567890A1", "d": "YYYY-MM-DD", "u": Espacenet link,
          "tag": sub-topic, "cc": country}
"""
import base64, datetime as dt, json, os, re, sys, time, urllib.parse, urllib.request

OPS = "https://ops.epo.org/3.2"
DAYS = int(os.environ.get("PATENT_DAYS", "30"))
PER_TAB = 10
MAX_PER_APPLICANT = 2
OFFICES = ("WO", "EP", "US", "BR")  # keep the feed readable in English, plus Brazil

# Each section: CPC classes + title/abstract keywords, and tags assigned from title words (first match wins).
SECTIONS = {
    "biocat": {
        "q": '(cpc=C12P or cpc=C12N9) and ta any "biocatalyst biocatalytic enzymatic transaminase ketoreductase lipase nitrilase imine reductase engineered enzyme"',
        "tags": [("transaminase", "Transaminases"), ("ketoreductase", "Ketoreductases"), ("reductase", "Reductases"),
                 ("lipase", "Lipases"), ("nitrilase", "Nitrilases"), ("oxidase", "Oxidases"), ("p450", "P450s"),
                 ("polymerase", "Polymerases"), ("cascade", "Enzyme cascades"), ("immobil", "Immobilized enzymes"),
                 ("variant", "Enzyme variants"), ("", "Biocatalysis")]},
    "pharma": {
        "q": '(cpc=A61K or cpc=A61P or cpc=C07K) and ta any "antibody conjugate bispecific mrna sirna oligonucleotide car-t gene therapy glp-1 degrader vaccine"',
        "tags": [("drug conjugate", "ADC"), ("conjugate", "ADC"), ("bispecific", "Bispecifics"), ("chimeric antigen", "Cell therapy"),
                 ("car-t", "Cell therapy"), ("car t", "Cell therapy"), ("mrna", "mRNA"), ("sirna", "RNAi"), ("oligonucleotide", "Oligonucleotides"),
                 ("aav", "Gene therapy"), ("gene therapy", "Gene therapy"), ("glp-1", "GLP-1 / metabolic"), ("glucagon", "GLP-1 / metabolic"),
                 ("degrad", "Degraders"), ("antibod", "Antibodies"), ("", "Therapeutics")]},
    "ag": {
        "q": '(cpc=A01N or cpc=A01P or cpc=A01H) and ta any "herbicide fungicide insecticide nematicide pesticidal biostimulant biological control crop plant"',
        "tags": [("herbicid", "Herbicides"), ("fungicid", "Fungicides"), ("insecticid", "Insecticides"), ("nematic", "Nematicides"),
                 ("biostimul", "Biostimulants"), ("bacillus", "Biocontrol"), ("trichoderma", "Biocontrol"), ("microb", "Biocontrol"),
                 ("biological", "Biocontrol"), ("gene edit", "Gene-edited crops"), ("crispr", "Gene-edited crops"), ("transgen", "Traits"),
                 ("event", "Traits"), ("seed", "Seed treatment"), ("", "Crop protection")]},
    "ag_br": {  # Brazilian filings, shown on the Agriculture tab
        "q": "pn=BR and (cpc=A01N or cpc=A01P)",
        "tags": [("herbic", "Herbicides"), ("fungic", "Fungicides"), ("insetic", "Insecticides"), ("insectic", "Insecticides"),
                 ("bacillus", "Biocontrol"), ("", "Crop protection")]},
    "synbio": {
        "q": '(cpc=C12N15 or cpc=C12N1 or cpc=C12P) and ta any "recombinant microorganism metabolic engineering synthetic biology yeast strain fermentation biosynthesis precision"',
        "tags": [("yeast", "Yeast"), ("saccharomyces", "Yeast"), ("escherichia", "E. coli"), ("e. coli", "E. coli"),
                 ("fermentation", "Fermentation"), ("milk", "Precision fermentation"), ("protein", "Protein production"),
                 ("biosynth", "Biosynthesis"), ("crispr", "Genome editing"), ("pathway", "Metabolic engineering"), ("", "Synthetic biology")]},
    "policy": {
        "q": '(cpc=A61K39 or cpc=A61P31 or cpc=C12Q1) and ta any "vaccine influenza antimicrobial antibiotic resistance pathogen diagnostic outbreak"',
        "tags": [("influenza", "Influenza"), ("h5n1", "Influenza"), ("antimicrobial", "AMR"), ("antibiotic", "AMR"), ("resistan", "AMR"),
                 ("vaccine", "Vaccines"), ("diagnos", "Diagnostics"), ("detect", "Diagnostics"), ("", "Infectious disease")]},
}


def http(url, data=None, headers=None, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, data=data, headers=headers or {})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", "replace")[:300]
            if e.code in (403, 429, 503) and i < tries - 1:  # throttled: wait and retry
                time.sleep(10 * (i + 1)); continue
            if e.code == 404:  # OPS answers 404 when a search has no results
                return None
            raise RuntimeError(f"HTTP {e.code} for {url[:120]}: {body}")


def token(key, secret):
    auth = base64.b64encode(f"{key}:{secret}".encode()).decode()
    body = http(f"{OPS}/auth/accesstoken", data=b"grant_type=client_credentials",
                headers={"Authorization": "Basic " + auth, "Content-Type": "application/x-www-form-urlencoded"})
    return json.loads(body)["access_token"]


def as_list(x):
    return x if isinstance(x, list) else ([] if x is None else [x])


def txt(x):
    return (x or {}).get("$", "") if isinstance(x, dict) else (x or "")


def parse(doc):
    d = doc.get("exchange-document", doc)
    b = d.get("bibliographic-data", {})
    cc, num, kind = d.get("@country", ""), d.get("@doc-number", ""), d.get("@kind", "")
    date = ""
    for di in as_list(b.get("publication-reference", {}).get("document-id")):
        if di.get("@document-id-type") == "docdb":
            date = txt(di.get("date")); break
    titles = as_list(b.get("invention-title"))
    title = next((txt(t) for t in titles if t.get("@lang") == "en"), txt(titles[0]) if titles else "")
    apps = as_list(b.get("parties", {}).get("applicants", {}).get("applicant"))
    app = next((txt(a.get("applicant-name", {}).get("name")) for a in apps if a.get("@data-format") == "epodoc"),
               txt(apps[0].get("applicant-name", {}).get("name")) if apps else "")
    app = re.sub(r"\s*\[[A-Z]{2}\]\s*$", "", app).strip()
    return {"cc": cc, "n": f"{cc}{num}{kind}", "num": num, "d": date, "t": title.strip(), "a": app,
            "fam": d.get("@family-id", "")}


def search(tok, cql, start, end, rng="1-100"):
    q = f"{cql} and pd within \"{start} {end}\""
    url = f"{OPS}/rest-services/published-data/search/biblio?q={urllib.parse.quote(q)}&Range={rng}"
    body = http(url, headers={"Authorization": "Bearer " + tok, "Accept": "application/json"})
    if not body:
        return []
    res = json.loads(body)["ops:world-patent-data"]["ops:biblio-search"]
    print(f"  {res.get('@total-result-count', '?')} hits", file=sys.stderr)
    docs = as_list(res.get("ops:search-result", {}).get("exchange-documents"))
    return [parse(x) for x in docs]


def tag_for(title, tags):
    t = title.lower()
    return next(lbl for kw, lbl in tags if kw in t)


def pick(rows, tags, offices):
    rows = [r for r in rows if r["t"] and r["d"] and r["cc"] in offices]
    rows.sort(key=lambda r: r["d"], reverse=True)
    out, fams, per_app = [], set(), {}
    for r in rows:
        if r["fam"] and r["fam"] in fams:
            continue
        k = r["a"].lower()
        if per_app.get(k, 0) >= MAX_PER_APPLICANT:
            continue
        fams.add(r["fam"]); per_app[k] = per_app.get(k, 0) + 1
        d = r["d"]
        title = r["t"][:1].upper() + r["t"][1:].lower() if r["t"].isupper() else r["t"]
        out.append({"t": title, "a": r["a"].title() if r["a"].isupper() else r["a"], "n": r["n"],
                    "d": f"{d[:4]}-{d[4:6]}-{d[6:8]}", "cc": r["cc"], "tag": tag_for(r["t"], tags),
                    "u": "https://worldwide.espacenet.com/patent/search?q=pn%3D" + r["n"]})
        if len(out) >= PER_TAB:
            break
    return out


def main():
    key, secret = os.environ.get("EPO_OPS_KEY"), os.environ.get("EPO_OPS_SECRET")
    if not key or not secret:
        print("EPO_OPS_KEY / EPO_OPS_SECRET not set; nothing to do.")
        return 0
    out_path = sys.argv[1] if len(sys.argv) > 1 else "data/patents.json"
    today = dt.date.today()
    start = (today - dt.timedelta(days=DAYS)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    tok = token(key, secret)
    tabs, failures = {}, []
    for name, sec in SECTIONS.items():
        print(f"{name}:", file=sys.stderr)
        rows = []
        try:
            offices = ("BR",) if name == "ag_br" else OFFICES
            cql = sec["q"] if name == "ag_br" else f"({sec['q']}) and (pn=WO or pn=EP or pn=US or pn=BR)"
            try:
                rows = search(tok, cql, start, end)
            except RuntimeError as e:  # office filter not accepted: drop it and filter locally
                print(f"  retry without office filter ({e})", file=sys.stderr)
                rows = search(tok, sec["q"], start, end)
            tabs[name] = pick(rows, sec["tags"], offices)
        except Exception as e:  # keep going; one section failing must not empty the others
            failures.append(f"{name}: {e}")
            print(f"  FAILED: {e}", file=sys.stderr)
        time.sleep(2)
    if not tabs:
        print("All sections failed:\n" + "\n".join(failures), file=sys.stderr)
        return 1
    old = {}
    if os.path.exists(out_path):
        try:
            old = json.load(open(out_path, encoding="utf-8")).get("tabs", {})
        except Exception:
            pass
    for name in SECTIONS:  # a failed section keeps yesterday's list
        if name not in tabs and name in old:
            tabs[name] = old[name]
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    json.dump({"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "window": {"from": f"{start[:4]}-{start[4:6]}-{start[6:]}", "to": f"{end[:4]}-{end[4:6]}-{end[6:]}"},
               "source": "EPO Open Patent Services", "tabs": tabs, "failures": failures},
              open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {out_path}: " + ", ".join(f"{k} {len(v)}" for k, v in tabs.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
