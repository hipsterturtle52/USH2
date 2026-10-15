#!/usr/bin/env python3
"""Static audit of the built study guide: structure, pools, balance, and lesson coverage."""
import json, re, sys, html
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
page = (ROOT / "clep-us-history-ii-study-guide.html").read_text(encoding="utf-8")
blob = re.search(r'<script type="application/json" id="data">(.*?)</script>', page, re.S).group(1)
D = json.loads(blob.replace("<\\/", "</"))
Q, U = D["questions"], D["units"]
meta = D["meta"]
problems = []

# 1. per-question structure
ids = Counter(q["id"] for q in Q)
problems += [f"duplicate id {i}" for i, c in ids.items() if c > 1]
for q in Q:
    tag = q["id"]
    if len(q["o"]) != 5: problems.append(f"{tag}: {len(q['o'])} options")
    if len(q["e"]) != 5 or any(not e.strip() for e in q["e"]): problems.append(f"{tag}: missing explanation")
    if not (isinstance(q["a"], int) and 0 <= q["a"] < 5): problems.append(f"{tag}: bad answer index")
    if not q["e"][q["a"]].strip(): problems.append(f"{tag}: correct option lacks explanation")
    if len(set(o.lower() for o in q["o"])) != 5: problems.append(f"{tag}: duplicate option text")
    if q["u"] not in range(1, 11): problems.append(f"{tag}: bad unit tag")
    if q["th"] not in {"pol", "soc", "eco", "cul", "dip"}: problems.append(f"{tag}: bad theme")
    if q["d"] not in "emh": problems.append(f"{tag}: bad difficulty")
    if q["pool"] not in {"quiz", "diag", "A", "B"}: problems.append(f"{tag}: bad pool")
    if re.search(r"all of the above|none of the above", " ".join(q["o"]), re.I): problems.append(f"{tag}: all/none of the above")

# 2. pools: disjoint, sized, every unit covered
pools = defaultdict(set)
for q in Q: pools[q["pool"]].add(q["id"])
for a in pools:
    for b in pools:
        if a < b and pools[a] & pools[b]: problems.append(f"pools {a}/{b} overlap")
if len(pools["A"]) != 120 or len(pools["B"]) != 120: problems.append("exam pools are not 120 each")
for p in ("diag", "A", "B"):
    missing = {u["n"] for u in U} - {q["u"] for q in Q if q["pool"] == p}
    if missing: problems.append(f"pool {p} missing units {missing}")
for u in U:
    nq = sum(q["u"] == u["n"] and q["pool"] == "quiz" for q in Q)
    if not 10 <= nq <= 15: problems.append(f"unit {u['n']} quiz has {nq} questions")

# 3. coverage: key terms of each correct answer should appear in the course text
def text_of(x): return html.unescape(re.sub(r"<[^>]+>", " ", x)).lower()
corpus = " ".join(text_of(u["lesson"] + " ".join(u["mustknow"]) + " ".join(e["t"] for e in u["timeline"]) + " ".join(c["f"] + " " + c["b"] for c in u["cards"])) for u in U)
STOP = set("which their there these those about would could should because between during after before other being where while under over into from with that this than what when were have been they them most more such also only many some much very upon its it's the and for are was not but who whom whose".split())
weak = []
for q in Q:
    words = [w for w in re.findall(r"[a-z][a-z'\-]{4,}", text_of(q["o"][q["a"]] + " " + q["s"])) if w not in STOP]
    if not words: continue
    hit = sum(w in corpus for w in words) / len(words)
    if hit < 0.6: weak.append((hit, q["id"], text_of(q["s"])[:90]))

# 4. report
print("=" * 72)
print("STRUCTURE:", "OK, every question has 5 options, exactly one keyed answer, 5 explanations, and unit/theme/difficulty/pool tags" if not problems else f"{len(problems)} PROBLEMS")
for p in problems: print("  -", p)
tot = len(Q); ncards = sum(len(u["cards"]) for u in U)
print(f"\nTOTALS: {len(U)} lessons, {tot} questions, {ncards} flashcards")
print(f"\n{'Unit':<46}{'Wt':>4}{'Lesson':>8}{'Qs':>5}{'Q%':>6}{'Cards':>7}{'C%':>6}{'Quiz':>6}{'Diag':>6}{'ExA':>5}{'ExB':>5}")
for u in U:
    uq = [q for q in Q if q["u"] == u["n"]]
    c = Counter(q["pool"] for q in uq)
    print(f"{str(u['n'])+'. '+u['title'][:42]:<46}{u['weight']:>3}%{u['minutes']:>5}min{len(uq):>5}{len(uq)/tot*100:>5.1f}%{len(u['cards']):>7}{len(u['cards'])/ncards*100:>5.1f}%{c['quiz']:>6}{c['diag']:>6}{c['A']:>5}{c['B']:>5}")
print("\nTHEMES (official vs. bank / exam A / exam B):")
for t in meta["thematic_weights"]:
    n = sum(q["th"] == t["id"] for q in Q)
    a = sum(q["th"] == t["id"] for q in Q if q["pool"] == "A"); b = sum(q["th"] == t["id"] for q in Q if q["pool"] == "B")
    print(f"  {t['name'][:55]:<57}{t['percent']:>3}%  bank {n/tot*100:5.1f}%  A {a/120*100:5.1f}%  B {b/120*100:5.1f}%")
period = {u["n"]: u["period"] for u in U}
for p, name, pc in (("early", "1865-1914", 30), ("late", "1915-present", 70)):
    n = sum(period[q["u"]] == p for q in Q)
    a = sum(period[q["u"]] == p for q in Q if q["pool"] == "A")
    print(f"  {name:<57}{pc:>3}%  bank {n/tot*100:5.1f}%  A {a/120*100:5.1f}%")
d = Counter(q["d"] for q in Q)
print(f"\nDIFFICULTY (target 30/50/20): easy {d['e']/tot*100:.1f}%  medium {d['m']/tot*100:.1f}%  hard {d['h']/tot*100:.1f}%")
for p in ("quiz", "diag", "A", "B"):
    pos = Counter("ABCDE"[q["a"]] for q in Q if q["pool"] == p)
    print(f"ANSWER POSITIONS {p:<5}", dict(sorted(pos.items())))
print(f"\nCOVERAGE: {len(weak)} questions whose correct-answer terms are <60% present in course text (review list):")
for h, i, s in sorted(weak): print(f"  {h:.2f} {i}: {s}")
sys.exit(1 if problems else 0)
