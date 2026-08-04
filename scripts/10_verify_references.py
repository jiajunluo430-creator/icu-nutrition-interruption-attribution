"""N2 step 10 - verify every intended reference against PubMed E-utilities.

Nothing enters the reference list unless PubMed returns a record whose title
matches the intended work. Unverifiable candidates are reported and dropped.
"""
import csv
import json
import re
import time
import urllib.parse
import urllib.request
import html
from difflib import SequenceMatcher
from pathlib import Path

OUT = Path(r"D:\N2_icu_nutrition_delivery_gap\03_outputs")
EUT = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

# key -> (what it is cited for, search query, expected title fragment)
CANDIDATES = [
    ("mimic", "MIMIC-IV database description", "36596836[uid]",
     "MIMIC-IV, a freely accessible electronic health record dataset"),
    ("eicu", "eICU database description", "30204154[uid]",
     "eICU Collaborative Research Database"),
    ("heyland2015", "iatrogenic underfeeding prevalence", "25086472[uid]",
     "prevalence of iatrogenic underfeeding"),
    ("orient", "prospective ICU feeding adequacy cohort", "41640734[uid]",
     "Nutritional practices and impact of feeding adequacy"),
    ("scoping2026", "2026 scoping review reporting 63.4% procedural attribution",
     "42293184[uid]", "Interruptions of enteral nutrition in intensive care units"),
    ("peev2015", "prospective study of causes of EN interruption", "24714361[uid]",
     "Causes and consequences of interrupted enteral nutrition"),
    ("uozumi2017", "single-centre survey of EN interruption", "28794882[uid]",
     "Interruption of enteral nutrition in the intensive care unit"),
    ("earlylate", "early vs delayed EN target trial emulation", "42375773[uid]",
     "Early versus delayed enteral nutrition in septic shock"),
    ("dosetransport", "MIMIC-IV nutrition dose transportability", "42349839[uid]",
     "Pre-transition nutrition dose and mortality"),
    ("espen2023", "ESPEN ICU nutrition guideline; energy and protein targets",
     "37517372[uid]", "ESPEN practical and partially revised guideline"),
    ("aspen2022", "ASPEN adult critical care nutrition guideline", "34784064[uid]",
     "Guidelines for the provision of nutrition support therapy in the adult critically ill patient"),
    ("esicm2017", "ESICM early enteral nutrition guideline", "28168570[uid]",
     "Early enteral nutrition in critically ill patients"),
    ("asa2023", "ASA preoperative fasting practice guideline", "36629465[uid]",
     "Practice Guidelines for Preoperative Fasting"),
    ("strobe", "STROBE reporting guideline", "17947786[uid]",
     "Strengthening the Reporting of Observational Studies in Epidemiology"),
    ("lipsitch", "negative controls for detecting confounding and bias", "20335814[uid]",
     "Negative controls: a tool for detecting confounding and bias"),
    ("hernan", "target-trial framing of observational analyses", "26994063[uid]",
     "Using Big Data to Emulate a Target Trial"),
]


def fetch(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def esearch(q):
    u = f"{EUT}/esearch.fcgi?db=pubmed&retmode=json&retmax=5&term={urllib.parse.quote(q)}"
    return json.loads(fetch(u))["esearchresult"].get("idlist", [])


def efetch(pmid):
    x = fetch(f"{EUT}/efetch.fcgi?db=pubmed&retmode=xml&id={pmid}")

    x = html.unescape(x)

    def one(tag, scope=None):
        src = scope if scope is not None else x
        m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", src, re.S)
        return re.sub("<[^>]+>", "", m.group(1)).strip() if m else ""

    # Year must come from JournalIssue/PubDate, not from PubMed history dates
    ji = re.search(r"<JournalIssue.*?</JournalIssue>", x, re.S)
    ji = ji.group(0) if ji else ""
    year = one("Year", ji)
    if not year:
        md = one("MedlineDate", ji)
        m = re.search(r"(\d{4})", md)
        year = m.group(1) if m else ""

    authors = []
    for a in re.findall(r"<Author[^>]*>(.*?)</Author>", x, re.S)[:20]:
        ln = re.search(r"<LastName>(.*?)</LastName>", a)
        ini = re.search(r"<Initials>(.*?)</Initials>", a)
        if ln:
            authors.append(f"{ln.group(1)} {ini.group(1) if ini else ''}".strip())
    doi = ""
    m = re.search(r'<ArticleId IdType="doi">(.*?)</ArticleId>', x)
    if m:
        doi = m.group(1).strip()
    return {
        "pmid": pmid, "title": one("ArticleTitle"),
        "journal": one("ISOAbbreviation") or one("Title"),
        "year": year, "volume": one("Volume", ji), "issue": one("Issue", ji),
        "pages": one("MedlinePgn"), "authors": authors, "doi": doi,
    }


rows, failures = [], []
for key, why, query, expect in CANDIDATES:
    try:
        ids = esearch(query)
        time.sleep(0.4)
        if not ids:
            failures.append({"key": key, "why": why, "reason": "no PubMed hit", "query": query})
            print(f"  FAIL  {key:14s} no hit")
            continue
        best, bestscore = None, 0.0
        for pid in ids[:3]:
            rec = efetch(pid)
            time.sleep(0.4)
            sc = SequenceMatcher(None, expect.lower(), rec["title"].lower()).ratio()
            if expect.lower() in rec["title"].lower():
                sc = max(sc, 0.95)
            if sc > bestscore:
                best, bestscore = rec, sc
        if bestscore < 0.60:
            failures.append({"key": key, "why": why, "reason":
                             f"best title match {bestscore:.2f}: {best['title'][:90]}",
                             "query": query})
            print(f"  FAIL  {key:14s} weak match {bestscore:.2f}")
            continue
        best.update({"key": key, "cited_for": why, "match_score": round(bestscore, 3)})
        rows.append(best)
        print(f"  OK    {key:14s} PMID {best['pmid']:>9s}  {best['title'][:64]}")
    except Exception as e:
        failures.append({"key": key, "why": why, "reason": f"error {e}", "query": query})
        print(f"  ERROR {key:14s} {e}")

with open(OUT / "references_verified.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["key", "cited_for", "pmid", "doi", "authors",
                                      "title", "journal", "year", "volume", "issue",
                                      "pages", "match_score"])
    w.writeheader()
    for r in rows:
        r = dict(r); r["authors"] = "; ".join(r["authors"])
        w.writerow({k: r.get(k, "") for k in w.fieldnames})

with open(OUT / "references_failed.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=["key", "why", "reason", "query"])
    w.writeheader(); w.writerows(failures)

print(f"\nverified {len(rows)} / {len(CANDIDATES)}; failed {len(failures)}")
if failures:
    print("\nFAILED (must be dropped or replaced):")
    for f_ in failures:
        print(f"  {f_['key']}: {f_['reason']}")
