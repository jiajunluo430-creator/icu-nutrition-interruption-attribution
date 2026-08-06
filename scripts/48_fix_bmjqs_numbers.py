"""N2 step 48 - correct two figures typed from memory, and narrow an over-broad check.

The causal-fraction CI and the median attribution-window length were written into the
draft from recollection rather than read from the deposited output. Both are corrected
here from review6_recompute.json.

The validator's banned-token list also rejected any string containing "replicat", which
catches legitimate uses: the manuscript must be able to say that the prespecified
replication FAILED, and "1,000 replicates" is the draw count. Narrowed to affirmative
replication claims only.
"""
import json
from pathlib import Path

ROOT = Path(r"D:\N2_icu_nutrition_delivery_gap")
R = json.load(open(ROOT / "03_outputs" / "review6" / "review6_recompute.json"))
af = R["attributable_fraction"]["target_only"]
med = R["window_length_h"]["median"]

p = ROOT / "07_manuscript" / "BMJQS_main_manuscript.md"
t = p.read_text(encoding="utf-8")
subs = [("(95% CI 12.1 to 15.2)", f"(95% CI {af['ci'][0]} to {af['ci'][1]})"),
        ("median 8.7 h", f"median {med} h")]
for a, b in subs:
    assert a in t, f"anchor not found: {a}"
    t = t.replace(a, b, 1)
    print(f"  {a}  ->  {b}")
assert "## References" in t
p.write_text(t, encoding="utf-8")

v = ROOT / "01_scripts" / "47_validate_bmjqs.py"
s = v.read_text(encoding="utf-8")
old = 'BANNED = [("replicat", "replication language"), ("Same answer", "two-database slogan"),'
new = ('# ban only AFFIRMATIVE replication claims. The manuscript must remain able to say\n'
       '# that the prespecified replication FAILED, and "1,000 replicates" is the draw count.\n'
       'BANNED = [("this replicated", "replication claim"),\n'
       '          ("replicating across", "replication claim"),\n'
       '          ("two independent databases", "replication claim"),\n'
       '          ("external validation", "validation claim"),\n'
       '          ("Same answer", "two-database slogan"),')
assert old in s
v.write_text(s.replace(old, new, 1), encoding="utf-8")
print("validator banned-token list narrowed to affirmative claims")
