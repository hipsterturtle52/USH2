#!/usr/bin/env python3
"""Build clep-us-history-ii-study-guide.html from src/ (single self-contained file).

Unit source format (src/units/uN.txt):
  @key: value          metadata (title, years, period, weight)
  @lesson              markdown-lite until next section
  @mustknow            "- item" lines
  @timeline            "year | text" or "year | text | key"
  @cards               "front :: back"
  @questions           blocks separated by blank lines:
                         Q <theme> <e|m|h>
                         > stimulus line (or "> T| cell | cell" table row; first row = header)
                         stem line(s)
                         + correct option || why it is right
                         - wrong option || why it is wrong   (x4)
"""
import html, json, random, re, sys
from pathlib import Path

ROOT = Path(__file__).parent
SRC = ROOT / "src"
OUT = ROOT / "clep-us-history-ii-study-guide.html"
THEMES = {"pol", "soc", "eco", "cul", "dip"}
SHORT = {"pol": "Political", "soc": "Social", "eco": "Economic", "cul": "Cultural/intellectual", "dip": "Diplomacy"}
# per-unit pool sizes: (diagnostic, exam A, exam B); remainder goes to the unit quiz
POOLS = {1: (2, 10, 10), 2: (4, 14, 14), 3: (3, 12, 12), 4: (3, 12, 12), 5: (3, 12, 12),
         6: (3, 10, 10), 7: (3, 13, 13), 8: (4, 16, 16), 9: (3, 11, 11), 10: (2, 10, 10)}
WPM = 130  # careful study reading speed for dense material

errors = []


def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", s)
    return s


def md(text):
    out, para, lst = [], [], []

    def flush():
        nonlocal para, lst
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para = []
        if lst:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in lst) + "</ul>")
            lst = []

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
        elif line.startswith("### "):
            flush(); out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            flush(); out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("!cec "):
            flush()
            parts = [p.strip() for p in line[5:].split("|")]
            if len(parts) != 3:
                errors.append(f"bad !cec line: {line}")
                continue
            lab = ["Cause", "Event", "Consequence"]
            boxes = [f'<div class="b"><b>{lab[i]}</b>{inline(p)}</div>' for i, p in enumerate(parts)]
            out.append('<div class="cec">' + '<div class="ar">→</div>'.join(boxes) + "</div>")
        elif line.startswith("- "):
            if para:
                out.append("<p>" + inline(" ".join(para)) + "</p>"); para = []
            lst.append(line[2:])
        else:
            if lst:
                flush()
            para.append(line)
    flush()
    return "\n".join(out)


def stim_html(lines):
    parts, rows = [], []
    for l in lines:
        if l.startswith("T|"):
            rows.append([c.strip() for c in l[2:].split("|")])
        else:
            if rows:
                parts.append(table(rows)); rows = []
            parts.append("<p>" + inline(l) + "</p>")
    if rows:
        parts.append(table(rows))
    return "".join(parts)


def table(rows):
    h = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
    b = "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rows[1:])
    return f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def parse_unit(path):
    n = int(re.search(r"u(\d+)", path.name).group(1))
    unit = {"n": n, "mustknow": [], "timeline": [], "cards": []}
    sections, cur = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^@(\w+)\s*:\s*(.*)$", line)
        if m:
            unit[m.group(1)] = m.group(2).strip(); continue
        m = re.match(r"^@(\w+)\s*$", line)
        if m:
            cur = m.group(1); sections[cur] = []; continue
        if cur:
            sections[cur].append(line)
    unit["weight"] = int(unit["weight"])
    lesson_src = "\n".join(sections.get("lesson", []))
    unit["lesson"] = md(lesson_src)
    words = len(re.findall(r"\w+", lesson_src))
    unit["words"] = words
    unit["minutes"] = max(5, round(words / WPM))
    for l in sections.get("mustknow", []):
        if l.strip().startswith("- "):
            unit["mustknow"].append(inline(l.strip()[2:]))
    for l in sections.get("timeline", []):
        if l.strip():
            p = [x.strip() for x in l.split("|")]
            unit["timeline"].append({"y": p[0], "t": inline(p[1]), "key": len(p) > 2 and p[2] == "key"})
    k = 0
    for l in sections.get("cards", []):
        if "::" in l:
            k += 1
            f, b = l.split("::", 1)
            unit["cards"].append({"id": f"u{n}c{k:02d}", "f": inline(f.strip()), "b": inline(b.strip())})
    qs = []
    blocks = re.split(r"\n\s*\n", "\n".join(sections.get("questions", [])).strip())
    for bi, blk in enumerate(blocks):
        lines = [l.rstrip() for l in blk.strip().splitlines() if l.strip()]
        if not lines:
            continue
        hdr = lines[0].split()
        qid = f"u{n}q{len(qs)+1:02d}"
        if hdr[0] != "Q" or len(hdr) != 3 or hdr[1] not in THEMES or hdr[2] not in "emh":
            errors.append(f"{path.name} block {bi+1}: bad header {lines[0]!r}"); continue
        stim, stem, opts = [], [], []
        for l in lines[1:]:
            if l.startswith("> "):
                stim.append(l[2:].strip())
            elif l[:2] in ("+ ", "- "):
                if "||" not in l:
                    errors.append(f"{qid}: option without explanation: {l!r}"); continue
                t, e = l[2:].split("||", 1)
                opts.append((l[0] == "+", t.strip(), e.strip()))
            else:
                stem.append(l.strip())
        if len(opts) != 5:
            errors.append(f"{qid}: {len(opts)} options (need 5): {' '.join(stem)[:60]}")
        if sum(o[0] for o in opts) != 1:
            errors.append(f"{qid}: {sum(o[0] for o in opts)} correct options")
        if any(not o[2] for o in opts):
            errors.append(f"{qid}: missing explanation")
        if any(re.search(r"\ball of the above\b|\bnone of the above\b", o[1], re.I) for o in opts):
            errors.append(f"{qid}: uses all/none of the above")
        if not stem:
            errors.append(f"{qid}: empty stem")
        qs.append({"id": qid, "u": n, "th": hdr[1], "d": hdr[2], "stim": stim, "stem": " ".join(stem), "opts": opts})
    unit["_qs"] = qs
    return unit


def assign_pools(unit):
    qs = unit["_qs"]
    n = unit["n"]
    dg, a, b = POOLS[n]
    quiz = len(qs) - dg - a - b
    if not 10 <= quiz <= 15:
        errors.append(f"unit {n}: quiz pool would be {quiz} (have {len(qs)} questions; need {dg+a+b+10}-{dg+a+b+15})")
    targets = {"A": a, "B": b, "diag": dg, "quiz": max(quiz, 0)}
    rng = random.Random(1000 + n)
    ordered = []
    for d in "emh":
        grp = [q for q in qs if q["d"] == d]
        rng.shuffle(grp)
        ordered += grp
    got = {k: 0 for k in targets}
    step = {k: (len(ordered) / t if t else float("inf")) for k, t in targets.items()}
    # systematic allocation: each pool takes items at evenly spaced positions, so every pool gets e/m/h in proportion
    nxt = {k: step[k] / 2 for k in targets}
    for i, q in enumerate(ordered):
        cands = [k for k in targets if got[k] < targets[k]]
        k = min(cands, key=lambda k: nxt[k])
        q["pool"] = k
        got[k] += 1
        nxt[k] += step[k]


def finalize_options(all_qs):
    out = []
    for pool in ["quiz", "diag", "A", "B"]:
        pq = sorted([q for q in all_qs if q.get("pool") == pool], key=lambda q: (q["u"], q["id"]))
        rng = random.Random(hash(pool) % 1000 if False else {"quiz": 11, "diag": 22, "A": 33, "B": 44}[pool])
        pos = [i % 5 for i in range(len(pq))]
        rng.shuffle(pos)
        for q, p in zip(pq, pos):
            right = [o for o in q["opts"] if o[0]]
            wrong = [o for o in q["opts"] if not o[0]]
            rng.shuffle(wrong)
            if len(right) != 1:
                continue
            ordered = wrong[:p] + right + wrong[p:]
            out.append({"id": q["id"], "u": q["u"], "th": q["th"], "d": q["d"], "pool": pool,
                        "s": inline(q["stem"]), "st": stim_html(q["stim"]),
                        "o": [inline(o[1]) for o in ordered], "e": [inline(o[2]) for o in ordered], "a": p})
    out.sort(key=lambda q: (q["u"], q["id"]))
    return out


def main():
    meta = json.loads((ROOT / "outline.json").read_text())
    for t in meta["thematic_weights"]:
        t["short"] = SHORT[t["id"]]
    units = [parse_unit(p) for p in sorted((SRC / "units").glob("u*.txt"), key=lambda p: int(re.search(r"\d+", p.name).group()))]
    all_qs = []
    for u in units:
        if u["_qs"]:
            assign_pools(u)
        all_qs += u["_qs"]
    questions = finalize_options(all_qs)
    # duplicate stem check
    seen = {}
    for q in questions:
        key = re.sub(r"\W+", "", (q["st"] + q["s"]).lower())[:160]
        if key in seen:
            errors.append(f"duplicate stem: {q['id']} ~ {seen[key]}")
        seen[key] = q["id"]
    period = {u["n"]: u["period"] for u in units}
    stats = {"total": len(questions),
             "theme": {t: sum(q["th"] == t for q in questions) for t in sorted(THEMES)},
             "period": {p: sum(period[q["u"]] == p for q in questions) for p in ("early", "late")},
             "diff": {d: sum(q["d"] == d for q in questions) for d in "emh"},
             "pool": {p: sum(q["pool"] == p for q in questions) for p in ("quiz", "diag", "A", "B")}}
    cheat_path = SRC / "cheatsheet.html"
    cheat = cheat_path.read_text(encoding="utf-8") if cheat_path.exists() else "<p>Cheat sheet coming soon.</p>"
    data = {"meta": meta, "stats": stats, "cheat": cheat, "questions": questions,
            "units": [{k: u[k] for k in ("n", "title", "years", "period", "weight", "minutes", "lesson", "mustknow", "timeline", "cards")} for u in units]}
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tpl = (SRC / "template.html").read_text(encoding="utf-8")
    OUT.write_text(tpl.replace('"__DATA__"', blob), encoding="utf-8")
    print(f"built {OUT.name}: {OUT.stat().st_size/1024:.0f} KB")
    print(f"{'unit':<5}{'wt':>4}{'words':>7}{'min':>5}{'Qs':>5}{'quiz':>5}{'cards':>6}  themes")
    for u in units:
        uq = [q for q in questions if q["u"] == u["n"]]
        th = " ".join(f"{t}:{sum(q['th']==t for q in uq)}" for t in ("pol", "soc", "eco", "cul", "dip"))
        print(f"{u['n']:<5}{u['weight']:>4}{u['words']:>7}{u['minutes']:>5}{len(uq):>5}{sum(q['pool']=='quiz' for q in uq):>5}{len(u['cards']):>6}  {th}")
    print("stats:", json.dumps(stats))
    if errors:
        print(f"\n{len(errors)} ERROR(S):")
        for e in errors:
            print("  -", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
