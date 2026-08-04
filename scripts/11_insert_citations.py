"""N2 step 11 - insert Frontiers-style numbered citations, renumber by first
appearance, build the reference list, and verify strict sequential ordering."""
import csv
import re
from pathlib import Path

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
OUT, MAN = ROOT / "03_outputs", ROOT / "07_manuscript"
MS = MAN / "FrontNutr_main_manuscript.md"

refs = {r["key"]: r for r in csv.DictReader(open(OUT / "references_verified.csv",
                                                 encoding="utf-8"))}

# Citation markers {{key,key}} are now written inline in the manuscript source,
# so no anchor matching is needed. This step only renders, numbers and verifies.
t = MS.read_text(encoding="utf-8")

# ---- number by order of first appearance
order, seen = [], set()
for m in re.finditer(r"\{\{([^}]+)\}\}", t):
    for k in m.group(1).split(","):
        if k not in seen:
            seen.add(k); order.append(k)
num = {k: i + 1 for i, k in enumerate(order)}

if not order:
    raise SystemExit(
        "ABORT: no citation markers found; manuscript already rendered. "
        "Re-running would overwrite the reference list with an empty one. "
        "Restore the marked-up source first.")

missing = [k for k in order if k not in refs]
if missing:
    raise SystemExit(f"cited but unverified: {missing}")
unused = [k for k in refs if k not in num]


def render(m):
    ks = m.group(1).split(",")
    ns = sorted(num[k] for k in ks)
    # collapse runs into ranges, Frontiers style
    parts, i = [], 0
    while i < len(ns):
        j = i
        while j + 1 < len(ns) and ns[j + 1] == ns[j] + 1:
            j += 1
        parts.append(str(ns[i]) if j == i else
                     (f"{ns[i]}, {ns[j]}" if j == i + 1 else f"{ns[i]}\u2013{ns[j]}"))
        i = j + 1
    return " (" + ", ".join(parts) + ")"


t = re.sub(r"\{\{([^}]+)\}\}", render, t)


# ---- reference list, Frontiers format
def fmt(r, n):
    au = [a.strip() for a in r["authors"].split(";") if a.strip()]
    au = ", ".join(au[:6]) + (", et al" if len(au) > 6 else "")
    pg = f":{r['pages']}" if r["pages"] else ""
    vol = r["volume"] or ""
    title = r["title"].rstrip(".")
    s = f"{n}. {au}. {title}. {r['journal']} ({r['year']})"
    s += f" {vol}{pg}." if vol else "."
    if r["doi"]:
        s += f" doi: {r['doi']}"
    return s


reflist = "\n\n".join(fmt(refs[k], num[k]) for k in order)
block = "\n## References\n\n" + reflist + "\n"

# References is pinned immediately BEFORE the back matter so that any later edit
# spanning the back matter cannot silently delete it (this has happened twice).
ANCHOR = "\n## Data availability statement"
if "\n## References\n" in t:
    t = re.sub(r"\n## References\n.*?(?=\n## |\Z)", block, t, flags=re.S)
elif ANCHOR in t:
    t = t.replace(ANCHOR, block + ANCHOR, 1)
else:
    t = t.replace("\n## Figure legends", block + "\n## Figure legends")

if "## References" not in t:
    raise SystemExit("ABORT: reference list was not inserted.")
MS.write_text(t, encoding="utf-8")

# ---- verify strict sequential ordering (body only; exclude the reference list,
# whose "(2015)" year fields would otherwise be read as citation numbers, and table
# rows, whose "(53-76)" IQRs look exactly like a citation range)
body = t.split("\n## References\n", 1)[0]
body = "\n".join(l for l in body.split("\n") if not l.lstrip().startswith("|"))
N = len(order)
cites = []
for m in re.finditer(r"\((\d+(?:[,\u2013\s]+\d+)*)\)", body):
    for part in re.split(r",\s*", m.group(1)):
        rng = re.match(r"^(\d+)\s*\u2013\s*(\d+)$", part.strip())
        if rng:  # "4\u20137" means 4,5,6,7 - expand it, do not read endpoints only
            cites.extend(range(int(rng.group(1)), int(rng.group(2)) + 1))
        elif part.strip().isdigit():
            cites.append(int(part.strip()))
cites = [c for c in cites if 1 <= c <= N]
first_seen, seq_ok, expected = {}, True, 1
for c in cites:
    if c not in first_seen:
        first_seen[c] = True
        if c != expected:
            seq_ok = False
            print(f"  ORDER ERROR: reference {c} first appears where {expected} expected")
        expected += 1

print(f"references verified & cited: {len(order)}")
print(f"unused verified references : {unused if unused else 'none'}")
print(f"in-text citation groups    : {len(re.findall(chr(92)+chr(40)+chr(92)+chr(100), body))}")
print(f"first-appearance order OK  : {seq_ok}")
print(f"numbering 1..{len(order)} complete: {sorted(first_seen) == list(range(1, len(order) + 1))}")

with open(OUT / "citation_order_check.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["number", "key", "pmid", "cited_for"])
    for k in order:
        w.writerow([num[k], k, refs[k]["pmid"], refs[k]["cited_for"]])
print("\n".join(f"  [{num[k]}] {refs[k]['pmid']}  {refs[k]['cited_for']}" for k in order))
