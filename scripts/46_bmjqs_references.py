"""N2 step 46 - build the BMJ Quality & Safety reference list.

The BMJ QS rewrite is shorter and cites a subset of the verified reference set. This
script maps each authored citation slot to an entry in the verified list, renumbers by
first appearance, converts Frontiers style to BMJ Vancouver style, and asserts the
result is sequential with every entry cited.

Frontiers:  A B, C D, E F, G H, I J, K L, et al. Title. Journal (2009) 35:1728-37. doi: 10.x
BMJ:        A B, C D, E F, et al. Title. Journal 2009;35:1728-37. doi:10.x

Idempotent: the resolved final-number -> verified-entry map is persisted, so re-running
rebuilds the same list rather than renumbering a second time.
"""
import json
import re
from pathlib import Path

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
MAN = ROOT / "07_manuscript"
MS_PATH = MAN / "BMJQS_main_manuscript.md"
MAPFILE = ROOT / "03_outputs" / "bmjqs_ref_map.json"

SRC = (MAN / "CritCare_main_manuscript.md").read_text(encoding="utf-8")
ms = MS_PATH.read_text(encoding="utf-8")

block = SRC.split("\n## References\n", 1)[1].split("\n## Declarations", 1)[0]
OLD = {}
for line in block.split("\n"):
    m = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
    if m:
        OLD[int(m.group(1))] = m.group(2)
assert len(OLD) == 49, len(OLD)

# authored slot -> verified entry number, written out so it can be checked by eye
AUTHORED = {
    1: 1, 2: 2, 3: 3, 4: 4,                  # underfeeding cohorts
    5: 19,                                    # interruption as the modifiable target
    6: 20,                                    # 2026 scoping review (the 63.4% figure)
    7: 21, 8: 22, 9: 23,                      # prospective bedside series
    10: 24, 11: 25, 12: 26,                   # protocols and QI programmes
    13: 27, 14: 28, 15: 29,                   # negative controls, falsification tests
    16: 30,                                   # MIMIC-IV
    17: 36, 18: 37,                           # exposure definition, target trials
    19: 43,                                   # eICU-CRD
    20: 41, 21: 42,                           # case-crossover, exchangeability
    22: 39,                                   # ASA preoperative fasting
    23: 7, 24: 40,                            # ESPEN, ESICM early EN
    25: 9, 26: 10, 27: 11, 28: 13, 29: 14,    # dose-outcome trials
    30: 38,                                   # STROBE
}

CITE = re.compile(r"\[(\d+(?:\s*[,\u2013-]\s*\d+)*)\]")


def expand(s):
    out = []
    for part in re.split(r",\s*", s):
        r = re.match(r"^(\d+)\s*[\u2013-]\s*(\d+)$", part.strip())
        out.extend(range(int(r.group(1)), int(r.group(2)) + 1) if r else [int(part.strip())])
    return out


def collapse(nums):
    nums = sorted(set(nums))
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        parts.append(f"{nums[i]}\u2013{nums[j]}" if j - i >= 2
                     else ", ".join(str(x) for x in nums[i:j + 1]))
        i = j + 1
    return "[" + ", ".join(parts) + "]"


def authors_trim(s):
    """BMJ house style: first three authors, then 'et al'."""
    m = re.match(r"^(.*?)\.\s+(.+)$", s, re.S)
    if not m:
        return s
    parts = [a.strip() for a in m.group(1).split(",") if a.strip() and a.strip() != "et al"]
    auth = ", ".join(parts[:3]) + ", et al" if len(parts) > 3 else ", ".join(parts)
    return f"{auth}. {m.group(2)}"


def to_bmj(s):
    s = re.sub(r"\s*\(((?:19|20)\d{2})\)\s+", r" \1;", s, count=1)
    s = authors_trim(s).replace("doi: ", "doi:")
    return re.sub(r"(\d);(\d+):(\d+)-(\d+)", "\\1;\\2:\\3\u2013\\4", s)


body = ms.split("\n## References", 1)[0]

if MAPFILE.exists():
    FINAL = {int(k): v for k, v in json.load(open(MAPFILE)).items()}
    print(f"reusing persisted map ({len(FINAL)} entries); no renumbering")
else:
    order, seen = [], set()
    for m in CITE.finditer(body):
        for n in expand(m.group(1)):
            assert n in AUTHORED, f"citation [{n}] has no mapping"
            if n not in seen:
                seen.add(n)
                order.append(n)
    unused = sorted(set(AUTHORED) - seen)
    assert not unused, f"mapped but never cited: {unused}"
    remap = {old: new for new, old in enumerate(order, 1)}
    body = CITE.sub(lambda m: collapse(remap[n] for n in expand(m.group(1))), body)
    FINAL = {new: AUTHORED[old] for old, new in remap.items()}
    json.dump({str(k): v for k, v in FINAL.items()}, open(MAPFILE, "w"), indent=2)
    print(f"renumbered {sum(1 for o, n in remap.items() if o != n)} of {len(remap)} "
          f"citations by first appearance")

lines = [f"{n}. {to_bmj(OLD[FINAL[n]])}" for n in sorted(FINAL)]
out = body.rstrip() + "\n\n## References\n\n" + "\n\n".join(lines) + "\n"
MS_PATH.write_text(out, encoding="utf-8")

chk = MS_PATH.read_text(encoding="utf-8").split("\n## References", 1)[0]
seq, s2 = [], set()
for m in CITE.finditer(chk):
    for n in expand(m.group(1)):
        if n not in s2:
            s2.add(n)
            seq.append(n)
assert seq == list(range(1, len(FINAL) + 1)), f"not sequential: {seq[:14]}"
print(f"ASSERT OK: {len(FINAL)} references, first-appearance order 1..{len(FINAL)}")
for l in lines[:2]:
    print("  " + l)
