"""N2 step 14 - expand the reference set toward the Frontiers in Nutrition norm.

Empirical target: recent Front Nutr ICU papers carry a median of 38 references
(n=25 sampled, range 24-95); comparable retrospective database studies cluster at
34-44. Every addition is placed at a real claim and PubMed-verified; nothing is
padding.
"""
import csv
import html
import json
import re
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

OUT = Path(r"D:\N2_icu_nutrition_delivery_gap\03_outputs")
EUT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

NEW = [
    ("prasad2013", "prespecified falsification endpoints", "23321761[uid]",
     "Prespecified falsification end points"),
    ("maclure1991", "case-crossover design", "1985444[uid]",
     "The case-crossover design"),
    ("mittleman2014", "exchangeability in the case-crossover design", "24756878[uid]",
     "Exchangeability in the case-crossover design"),
]


def fetch(u):
    return urllib.request.urlopen(u, timeout=30).read().decode("utf-8", "replace")


def efetch(pmid):
    x = html.unescape(fetch(f"{EUT}/efetch.fcgi?db=pubmed&retmode=xml&id={pmid}"))

    def one(tag, scope=None):
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", scope if scope is not None else x, re.S)
        return re.sub("<[^>]+>", "", m.group(1)).strip() if m else ""

    ji = re.search(r"<JournalIssue.*?</JournalIssue>", x, re.S)
    ji = ji.group(0) if ji else ""
    year = one("Year", ji) or (re.search(r"(\d{4})", one("MedlineDate", ji)) or [None])
    if not isinstance(year, str):
        m = re.search(r"(\d{4})", one("MedlineDate", ji))
        year = m.group(1) if m else ""
    au = []
    for a in re.findall(r"<Author[^>]*>(.*?)</Author>", x, re.S)[:20]:
        ln = re.search(r"<LastName>(.*?)</LastName>", a)
        ini = re.search(r"<Initials>(.*?)</Initials>", a)
        if ln:
            au.append(f"{ln.group(1)} {ini.group(1) if ini else ''}".strip())
    doi = re.search(r'<ArticleId IdType="doi">(.*?)</ArticleId>', x)
    return {"pmid": pmid, "title": one("ArticleTitle"),
            "journal": one("ISOAbbreviation") or one("Title"), "year": year,
            "volume": one("Volume", ji), "issue": one("Issue", ji),
            "pages": one("MedlinePgn"), "authors": "; ".join(au),
            "doi": doi.group(1).strip() if doi else ""}


existing = list(csv.DictReader(open(OUT / "references_verified.csv", encoding="utf-8")))
have = {r["pmid"] for r in existing}
rows, fails = [], []

for key, why, query, expect in NEW:
    try:
        u = f"{EUT}/esearch.fcgi?db=pubmed&retmode=json&retmax=5&term={urllib.parse.quote(query)}"
        ids = json.loads(fetch(u))["esearchresult"]["idlist"]
        time.sleep(0.35)
        if not ids:
            fails.append((key, "no hit")); print(f"  FAIL {key:15s} no hit"); continue
        best, sc = None, 0.0
        for pid in ids[:3]:
            rec = efetch(pid); time.sleep(0.35)
            s = SequenceMatcher(None, expect.lower(), rec["title"].lower()).ratio()
            if expect.lower() in rec["title"].lower():
                s = max(s, 0.95)
            if s > sc:
                best, sc = rec, s
        if sc < 0.62:
            fails.append((key, f"weak {sc:.2f}: {best['title'][:70]}"))
            print(f"  FAIL {key:15s} weak {sc:.2f}"); continue
        if best["pmid"] in have:
            fails.append((key, "duplicate of existing")); print(f"  DUP  {key:15s}"); continue
        have.add(best["pmid"])
        best.update({"key": key, "cited_for": why, "match_score": round(sc, 3)})
        rows.append(best)
        print(f"  OK   {key:15s} {best['year']}  {best['title'][:60]}")
    except Exception as e:
        fails.append((key, f"error {e}")); print(f"  ERR  {key:15s} {e}")

allrefs = existing + rows
with open(OUT / "references_verified.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["key", "cited_for", "pmid", "doi", "authors",
                                      "title", "journal", "year", "volume", "issue",
                                      "pages", "match_score"])
    w.writeheader()
    for r in allrefs:
        w.writerow({k: r.get(k, "") for k in w.fieldnames})

print(f"\nadded {len(rows)}; total now {len(allrefs)}")
if fails:
    print("\nnot added:")
    for k, r in fails:
        print(f"  {k}: {r}")
