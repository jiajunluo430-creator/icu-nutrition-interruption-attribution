"""N2 step 35 - renumber citations in the Critical Care manuscript by first appearance.

Moving the eICU external validation into Methods made reference 43 appear before 38-42,
breaking sequential order. This pass rebuilds the numbering from the body text and
reorders the reference list to match, then asserts the result is 1..N with no gaps and
no uncited entries.

Idempotent: running it on an already-ordered manuscript is a no-op.
"""
import re
from pathlib import Path

MS = Path(r"D:\N2_icu_nutrition_delivery_gap\07_manuscript\CritCare_main_manuscript.md")
t = MS.read_text(encoding="utf-8")

HEAD = "\n## References\n"
assert HEAD in t, "no References section"
body, rest = t.split(HEAD, 1)
# the reference list ends where the next top-level section begins
m = re.search(r"\n## (?!References)", rest)
reflist, tail = (rest[:m.start()], rest[m.start():]) if m else (rest, "")

refs = {}
for line in reflist.split("\n"):
    mm = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
    if mm:
        refs[int(mm.group(1))] = mm.group(2)
N = len(refs)
assert N > 0, "no reference entries parsed"
assert sorted(refs) == list(range(1, N + 1)), f"reference list not 1..{N}"

CITE = re.compile(r"\[(\d+(?:\s*[,\u2013-]\s*\d+)*)\]")


def expand(s):
    out = []
    for part in re.split(r",\s*", s):
        r = re.match(r"^(\d+)\s*[\u2013-]\s*(\d+)$", part.strip())
        if r:
            out.extend(range(int(r.group(1)), int(r.group(2)) + 1))
        else:
            out.append(int(part.strip()))
    return out


# --- first-appearance order over the body only
order, seen = [], set()
for mm in CITE.finditer(body):
    for n in expand(mm.group(1)):
        assert 1 <= n <= N, f"citation [{n}] has no reference entry"
        if n not in seen:
            seen.add(n)
            order.append(n)

uncited = [n for n in range(1, N + 1) if n not in seen]
assert not uncited, f"reference entries never cited: {uncited}"
remap = {old: new for new, old in enumerate(order, start=1)}


def collapse(nums):
    """Render a sorted list as a citation group, collapsing runs of >=3 into ranges."""
    nums = sorted(set(nums))
    parts, i = [], 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        if j - i >= 2:
            parts.append(f"{nums[i]}\u2013{nums[j]}")
        else:
            parts.extend(str(x) for x in nums[i:j + 1])
        i = j + 1
    return "[" + ", ".join(parts) + "]"


new_body = CITE.sub(lambda mm: collapse(remap[n] for n in expand(mm.group(1))), body)
new_reflist = "\n" + "\n\n".join(f"{new}. {refs[old]}" for new, old in enumerate(order, 1)) + "\n"

out = new_body + HEAD + new_reflist + tail
assert "## References" in out
assert out.count("## Declarations") == 1
MS.write_text(out, encoding="utf-8")

# --- verify the written file
chk = MS.read_text(encoding="utf-8")
cbody = chk.split(HEAD, 1)[0]
seq, s2 = [], set()
for mm in CITE.finditer(cbody):
    for n in expand(mm.group(1)):
        if n not in s2:
            s2.add(n)
            seq.append(n)
assert seq == list(range(1, N + 1)), f"still not sequential: first 12 = {seq[:12]}"
moved = sum(1 for o, n in remap.items() if o != n)
print(f"renumbered {moved} of {N} references; first-appearance order now 1..{N}")
print(f"ASSERT OK: sequential, no gaps, all {N} cited")
