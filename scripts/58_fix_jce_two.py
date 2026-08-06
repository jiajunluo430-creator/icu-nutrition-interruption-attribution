"""N2 step 58 - two corrections to the JCE version.

1. The manuscript renders tau to one decimal place throughout (7.1 pp); the validator
   was testing the stored two-decimal value (7.08). The check now tests the same
   one-decimal rendering the text uses, so it still catches a genuine mismatch.
2. The abstract was two words over the 300-word limit.
"""
import json
import re
from pathlib import Path

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
SH = json.load(open(ROOT / "03_outputs" / "review6" / "hospital_shrinkage.json"))

v = ROOT / "01_scripts" / "57_validate_and_package_jce.py"
s = v.read_text(encoding="utf-8")
old = '("tau", SH["tau_pp"]), ("ICC", SH["icc"]),'
new = '("tau (1 dp, as rendered in text)", f\'{SH["tau_pp"]:.1f}\'), ("ICC", SH["icc"]),'
assert old in s
v.write_text(s.replace(old, new, 1), encoding="utf-8")
print(f"validator now tests tau as rendered: {SH['tau_pp']:.1f}")

p = ROOT / "07_manuscript" / "JCE_main_manuscript.md"
t = p.read_text(encoding="utf-8")
subs = [
    ("Studies using routinely collected electronic health record (EHR) data routinely "
     "attribute an event to a cause because the two were recorded close together in time.",
     "Studies using routinely collected electronic health record (EHR) data often attribute "
     "an event to a cause because the two were recorded close together in time."),
    ("We quantify that background rate, show how to correct for it using data the analysis "
     "already holds, and examine whether the background rate is stable enough for "
     "uncorrected attribution percentages to be compared across sites.",
     "We quantify that background rate, correct for it using data the analysis already "
     "holds, and examine whether it is stable enough for uncorrected attribution "
     "percentages to be compared across sites."),
]
for a, b in subs:
    assert a in t, a[:60]
    t = t.replace(a, b, 1)
assert "## References" in t
p.write_text(t, encoding="utf-8")

ab = t.split("## Abstract", 1)[1].split("**Keywords:**", 1)[0]
n = sum(1 for w in re.sub(r"[*`]", "", ab).split() if re.search(r"[A-Za-z0-9]", w))
print(f"abstract now {n} words (limit 300)")
