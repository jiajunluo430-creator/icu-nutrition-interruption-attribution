"""N2 step 55 - reference list for the Journal of Clinical Epidemiology version.

The JCE rewrite cites the same works as the BMJ QS version but in a different order,
because the framing leads with the method rather than the clinical topic. Slot numbers
were authored against the BMJ QS numbering; this script renumbers by first appearance
and emits Elsevier numbered style.

BMJ:       A B, C D, E F, et al. Title. Journal 2009;35:1728-37. doi:10.x
Elsevier:  A B, C D, E F, G H, I J, K L, et al. Title. J Abbrev 2009;35:1728-37.
"""
import json
import re
from pathlib import Path

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
MAN, OUT = ROOT / "07_manuscript", ROOT / "03_outputs"
MS_PATH = MAN / "JCE_main_manuscript.md"
MAPFILE = OUT / "jce_ref_map.json"

# verified entries, parsed from the Critical Care manuscript's list
SRC = (MAN / "CritCare_main_manuscript.md").read_text(encoding="utf-8")
block = SRC.split("\n## References\n", 1)[1].split("\n## Declarations", 1)[0]
OLD = {}
for line in block.split("\n"):
    m = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
    if m:
        OLD[int(m.group(1))] = m.group(2)
assert len(OLD) == 49

# the JCE draft was authored using the BMJ QS final numbering
BMJ = {int(k): v for k, v in json.load(open(OUT / "bmjqs_ref_map.json")).items()}

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


def to_elsevier(s):
    """Elsevier numbered style: up to six authors then et al, no doi, en-dash pages."""
    s = re.sub(r"\s*\(((?:19|20)\d{2})\)\s+", r" \1;", s, count=1)
    s = re.sub(r"\s*doi:\s*\S+\s*$", "", s).rstrip()
    m = re.match(r"^(.*?)\.\s+(.+)$", s, re.S)
    if m:
        auth = [a.strip() for a in m.group(1).split(",")
                if a.strip() and a.strip() != "et al"]
        head = ", ".join(auth[:6]) + (", et al" if len(auth) > 6 else "")
        s = f"{head}. {m.group(2)}"
    s = re.sub(r"(\d);(\d+):(\d+)-(\d+)", "\\1;\\2:\\3\u2013\\4", s)
    return s if s.endswith(".") else s + "."


body = MS_PATH.read_text(encoding="utf-8").split("\n## References", 1)[0]

if MAPFILE.exists():
    FINAL = {int(k): v for k, v in json.load(open(MAPFILE)).items()}
    print(f"reusing persisted map ({len(FINAL)} entries); no renumbering")
else:
    order, seen = [], set()
    for m in CITE.finditer(body):
        for nn in expand(m.group(1)):
            assert nn in BMJ, f"citation [{nn}] is not in the BMJ QS map"
            if nn not in seen:
                seen.add(nn)
                order.append(nn)
    dropped = sorted(set(BMJ) - seen)
    remap = {old: new for new, old in enumerate(order, 1)}
    body = CITE.sub(lambda m: collapse(remap[n] for n in expand(m.group(1))), body)
    FINAL = {new: BMJ[old] for old, new in remap.items()}
    json.dump({str(k): v for k, v in FINAL.items()}, open(MAPFILE, "w"), indent=2)
    print(f"renumbered by first appearance; {len(FINAL)} cited")
    if dropped:
        print(f"  not cited in the JCE version and therefore dropped: {dropped}")

lines = [f"[{n}] {to_elsevier(OLD[FINAL[n]])}" for n in sorted(FINAL)]
out = body.rstrip() + "\n\n## References\n\n" + "\n\n".join(lines) + "\n"
MS_PATH.write_text(out, encoding="utf-8")

chk = MS_PATH.read_text(encoding="utf-8").split("\n## References", 1)[0]
seq, s2 = [], set()
for m in CITE.finditer(chk):
    for nn in expand(m.group(1)):
        if nn not in s2:
            s2.add(nn)
            seq.append(nn)
assert seq == list(range(1, len(FINAL) + 1)), f"not sequential: {seq[:14]}"
assert "doi:" not in "\n".join(lines), "Elsevier style should not carry doi here"
print(f"ASSERT OK: {len(FINAL)} references, first-appearance order 1..{len(FINAL)}")
for l in lines[:2]:
    print("  " + l)
