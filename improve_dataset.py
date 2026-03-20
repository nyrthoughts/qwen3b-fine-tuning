#!/usr/bin/env python3
"""Improve existing manufacturing QA dataset by rewriting inputs for better SFT quality."""

import json
import random
import shutil
from collections import Counter
from pathlib import Path

random.seed(42)

# ============================================================================
# IMPLICIT DEFECT DESCRIPTIONS (don't use the exact defect_type string)
# ============================================================================

IMPLICIT_DEFECTS = {
    "scratch": [
        "marks on the surface", "visible scoring", "the finish is damaged",
        "surface looks roughed up", "something scraped against it",
        "you can see lines across the surface", "the coating got torn up",
        "a mark that runs along the edge", "surface damage near the edge",
    ],
    "dent": [
        "it's pushed in on one side", "there's a depression in the metal",
        "looks like something hit it", "the surface isn't flat anymore",
        "you can feel a dip when you run your hand over it",
        "it's deformed near the corner", "the shape is off",
        "a visible impact mark",
    ],
    "crack": [
        "there's a line running through it", "it split near the edge",
        "you can see it's starting to break apart", "the material gave way",
        "there's a visible fracture", "it's compromised structurally",
        "I can see daylight through the joint", "a thin line through the body",
    ],
    "misalignment": [
        "it's not sitting straight", "the fit is off", "it's shifted to one side",
        "the holes don't line up", "it's about 2mm off from where it should be",
        "the mounting points aren't matching", "it's crooked",
        "the two halves don't meet flush",
    ],
    "wrong label": [
        "the sticker doesn't match the part number", "the label says something different",
        "it's tagged with the wrong SKU", "the barcode doesn't scan right",
        "the identification is incorrect", "the marking doesn't correspond to what's inside",
        "somebody put the wrong tag on it",
    ],
    "missing component": [
        "there's a part missing from the assembly", "one piece isn't there",
        "the kit is incomplete", "we're short one component",
        "when I opened it up, a part was missing", "it shipped without the insert",
        "the sub-assembly is incomplete",
    ],
    "loose fastener": [
        "the bolt isn't tight", "it wobbles when you touch it",
        "I can turn it by hand", "it's not torqued properly",
        "the connection is loose", "the screw backs out easily",
        "there's play in the joint",
    ],
    "contamination": [
        "there's something on the surface that shouldn't be there",
        "I found foreign material inside", "it's got residue all over it",
        "there are particles stuck to it", "it looks dirty, not just dust",
        "something got into the assembly", "the surface is contaminated",
    ],
    "leak": [
        "fluid is coming out where it shouldn't", "there's a wet spot forming",
        "I can see dripping near the joint", "it's losing pressure slowly",
        "there's moisture on the outside", "something is seeping through",
        "the seal isn't holding",
    ],
    "welding defect": [
        "the weld doesn't look right", "there are voids in the joint",
        "the bead is uneven", "it didn't fuse properly",
        "the weld has porosity", "the joint looks weak",
        "you can see undercut along the weld line",
    ],
    "paint defect": [
        "the finish is uneven", "the paint didn't stick in places",
        "there are runs in the coating", "the color doesn't match",
        "you can see the base metal through the paint", "there are bubbles in the finish",
        "the coating is peeling off",
    ],
    "dimension out of tolerance": [
        "it doesn't fit in the fixture", "the measurement is off",
        "it's oversized by about half a mil", "the diameter is wrong",
        "it won't mate with the next part", "the gauge shows it's out of spec",
        "the dimensions don't match the drawing",
    ],
    "packaging damage": [
        "the box is crushed on one side", "the packaging got torn",
        "the protective wrap failed", "the carton is wet",
        "the padding wasn't enough", "the parts shifted inside the box",
        "the outer packaging is compromised",
    ],
    "sensor failure": [
        "the readings are all over the place", "the sensor isn't responding",
        "we're getting erratic values", "the output is flatlined",
        "it's reading way outside normal range", "the signal keeps dropping",
        "the display shows an error code",
    ],
    "assembly error": [
        "it was put together wrong", "the sequence was off",
        "parts are in the wrong position", "it doesn't look like the work instruction",
        "the orientation is reversed", "two parts got swapped",
        "it was assembled with the wrong revision components",
    ],
}

EXPLICIT_DEFECTS = {
    "scratch": ["scratch", "scuff mark", "abrasion", "surface scratch", "scoring"],
    "dent": ["dent", "ding", "indentation", "impact mark"],
    "crack": ["crack", "fracture", "hairline crack", "split"],
    "misalignment": ["misalignment", "alignment issue", "offset"],
    "wrong label": ["wrong label", "mislabel", "labeling error"],
    "missing component": ["missing part", "missing component", "absent piece"],
    "loose fastener": ["loose bolt", "loose screw", "untightened fastener"],
    "contamination": ["contamination", "foreign debris", "residue buildup"],
    "leak": ["leak", "seepage", "drip"],
    "welding defect": ["weld flaw", "bad weld", "weld porosity"],
    "paint defect": ["paint issue", "coating defect", "finish problem"],
    "dimension out of tolerance": ["out-of-spec dimension", "tolerance issue", "size deviation"],
    "packaging damage": ["damaged box", "packaging failure", "shipping damage"],
    "sensor failure": ["sensor fault", "bad sensor", "sensor malfunction"],
    "assembly error": ["assembly mistake", "build error", "wrong assembly"],
}

OPERATORS = [
    "Mike", "Sarah", "James", "Linda", "Carlos", "Priya", "Tom",
    "Angela", "Wei", "David", "Maria", "Steve", "Rachel", "Omar", "Kim",
    "Dan", "Yuki", "Chris", "Nina", "Raj", "Elena", "Marco", "Jen",
    "Derek", "Fatima", "Greg", "Hana", "Ivan", "Lisa", "Pete",
]

SHIFTS = ["morning shift", "afternoon shift", "night shift", "day shift", "second shift", "third shift"]

TIMES = [
    "around 6:30 AM", "about an hour ago", "just before lunch",
    "right after changeover", "mid-shift", "at the start of the run",
    "near the end of our batch", "about 20 minutes ago",
    "first thing this morning", "around 2 PM", "during the 10 o'clock break",
    "after the break", "toward end of shift", "early into the run",
]

QUANTITIES = [
    "3 units", "a couple of pieces", "about 5 or 6 parts", "at least 10",
    "one unit", "a handful", "the whole tray", "2 out of 20",
    "maybe a dozen", "7 consecutive parts", "every other one for a while",
    "4 so far", "15+ units", "two batches worth", "the last 8 parts",
]

CAUSE_INTROS = [
    "Looks like", "Probably", "We think it's", "My guess is",
    "Could be", "Might be", "Seems like", "Pretty sure it's",
    "Most likely", "I'd bet it's", "Suspect", "Thinking it's",
    "Not 100% sure but probably", "Based on what I see,",
    "Possibly", "Our theory is", "Evidence points to",
]

# ============================================================================
# BUILDING BLOCKS — composable sentence fragments
# ============================================================================

def _pick_defect(defect_type: str, use_implicit: bool = None) -> str:
    """Pick a defect description."""
    if use_implicit is None:
        use_implicit = random.random() < 0.55
    if use_implicit:
        return random.choice(IMPLICIT_DEFECTS[defect_type])
    return random.choice(EXPLICIT_DEFECTS[defect_type])


def _cause_phrase(cause: str) -> str:
    intro = random.choice(CAUSE_INTROS)
    return f"{intro} {cause}"


def _maybe(text: str, prob: float = 0.5) -> str:
    return text if random.random() < prob else ""


# -- LOCATION SENTENCES --
def _loc_sentences(line: str, part: str) -> list[str]:
    """Pool of sentences that establish where/what."""
    op = random.choice(OPERATORS)
    shift = random.choice(SHIFTS)
    time = random.choice(TIMES)
    qty = random.choice(QUANTITIES)
    return [
        f"On {line}, checking the {part}.",
        f"This is from {line} — the {part}.",
        f"{line}, {part} batch.",
        f"Happened at {line} on the {part}.",
        f"{op} was working {line} when they found this on a {part}.",
        f"Production on {line}, the {part} came out wrong.",
        f"{shift} at {line} — issue with the {part}.",
        f"While running the {part} on {line}.",
        f"The {part} off {line} has a problem.",
        f"Inspecting {part} units from {line}.",
        f"We pulled {qty} {part} from {line}.",
        f"Caught this on {line} {time}.",
        f"{op} noticed something on the {part}, {line}.",
        f"{line} — spotted an issue with the {part} around {time}.",
        f"The last batch of {part} from {line} isn't right.",
        f"Station report: {line}, part type {part}.",
        f"During the {shift} run on {line}, the {part} had an issue.",
        f"Coming off {line}: {part}.",
    ]


# -- DEFECT SENTENCES --
def _defect_sentences(defect_type: str) -> list[str]:
    """Pool of sentences describing the defect."""
    d_impl = random.choice(IMPLICIT_DEFECTS[defect_type])
    d_expl = random.choice(EXPLICIT_DEFECTS[defect_type])
    return [
        f"Found {d_impl}.",
        f"We're seeing {d_impl}.",
        f"There's {d_expl}.",
        f"Issue: {d_impl}.",
        f"Defect — {d_impl}.",
        f"The part has {d_impl}.",
        f"Confirmed {d_expl}.",
        f"{d_impl.capitalize()}.",
        f"Looks like {d_impl}.",
        f"Noticed {d_impl}.",
        f"Clear case of {d_expl}.",
        f"Visual inspection shows {d_impl}.",
        f"Problem: {d_expl}.",
        f"Not acceptable — {d_impl}.",
    ]


# -- CAUSE SENTENCES --
def _cause_sentences(cause: str) -> list[str]:
    """Pool of sentences about the cause."""
    intro = random.choice(CAUSE_INTROS)
    return [
        f"{intro} {cause}.",
        f"Cause: {cause}.",
        f"We think it's due to {cause}.",
        f"Likely happened because of {cause}.",
        f"Suspecting {cause}.",
        f"Traced back to {cause}.",
        f"Appears to be from {cause}.",
        f"Best explanation so far: {cause}.",
        f"Pointing at {cause} as the reason.",
        f"The evidence suggests {cause}.",
        f"Working theory: {cause}.",
    ]


# -- FILLER/CONTEXT SENTENCES (optional) --
def _filler_sentences(line: str, part: str) -> list[str]:
    """Optional context to add realism. Parameterized for variety."""
    op = random.choice(OPERATORS)
    op2 = random.choice(OPERATORS)
    qty = random.choice(QUANTITIES)
    time = random.choice(TIMES)
    shift = random.choice(SHIFTS)
    lot = f"LOT-{random.randint(1000, 9999)}"
    wo = f"WO-{random.randint(200, 999)}"
    return [
        f"Affected {qty}.",
        f"First noticed {time}.",
        f"{op} pulled the parts.",
        f"Set aside for review.",
        f"QC is aware.",
        f"We stopped the run temporarily.",
        f"Tagged for further inspection.",
        f"This wasn't caught by the in-line check.",
        f"Happened during {shift}.",
        f"{op} reported it to {op2}.",
        f"Batch {lot} affected.",
        f"Ref: {wo}.",
        f"About {qty} in the reject bin.",
        f"We ran {qty} before catching it.",
        f"Found {time} on the {part}.",
        f"Other {part} units look OK so far.",
        f"Same thing happened last month on {line}.",
        f"No prior issues with this {part} batch.",
        f"The reject rate on {line} spiked.",
        f"Checked the previous batch — those are fine.",
        f"Only affects the {part} from today's run.",
        f"We'll know more after engineering reviews it.",
        f"Holding shipment for now.",
        f"Operator log updated.",
        f"Added to the daily scrap report.",
        f"Happened on {qty}.",
        f"{op} is documenting the details.",
        f"Not our usual failure mode.",
        f"This batch was supposed to ship today.",
        f"The gauge confirmed it.",
        f"Visual check only so far.",
        f"Ran the last {qty} through again — same result.",
        f"The customer spec is tight on this one.",
        f"Upstream station didn't flag anything.",
        f"We swapped the {part} and the replacement is fine.",
        f"This started after the tooling change.",
        f"The {part} from the same lot last week was OK.",
    ]


# ============================================================================
# COMPOSER — builds inputs from building blocks
# ============================================================================

def compose_input(defect_type: str, line: str, part: str, cause: str) -> str:
    """Compose an input by picking and shuffling sentence fragments."""
    loc_pool = _loc_sentences(line, part)
    defect_pool = _defect_sentences(defect_type)
    cause_pool = _cause_sentences(cause)
    filler_pool = _filler_sentences(line, part)

    loc = random.choice(loc_pool)
    defect_sent = random.choice(defect_pool)
    cause_sent = random.choice(cause_pool)

    # Core: always location + defect + cause (in varied order)
    core = [loc, defect_sent, cause_sent]

    # Sometimes add 1-2 filler sentences
    n_filler = random.choices([0, 1, 2], weights=[0.3, 0.5, 0.2])[0]
    fillers = random.sample(filler_pool, min(n_filler, len(filler_pool)))
    core.extend(fillers)

    # Shuffle order with constraints:
    # - location tends to come first (70%) or second (30%)
    # - cause tends to come last (60%) or second-to-last (40%)
    order_strategy = random.random()
    if order_strategy < 0.4:
        # LOC -> DEFECT -> CAUSE -> fillers
        sentences = [loc, defect_sent, cause_sent] + fillers
    elif order_strategy < 0.65:
        # LOC -> CAUSE -> DEFECT -> fillers
        sentences = [loc, cause_sent, defect_sent] + fillers
    elif order_strategy < 0.8:
        # DEFECT -> LOC -> CAUSE -> fillers
        sentences = [defect_sent, loc, cause_sent] + fillers
    elif order_strategy < 0.9:
        # LOC -> fillers -> DEFECT -> CAUSE
        sentences = [loc] + fillers + [defect_sent, cause_sent]
    else:
        # Random shuffle
        random.shuffle(core)
        sentences = core + fillers

    return " ".join(sentences)


# ============================================================================
# STYLE WRAPPERS — add stylistic flavor on top of composed content
# ============================================================================

def style_raw(text: str) -> str:
    """As-is, no modification."""
    return text

def style_slack(text: str) -> str:
    """Lowercase first letter, informal touches."""
    if text and text[0].isupper():
        text = text[0].lower() + text[1:]
    # Random informal ending
    endings = [
        "", "", "", "",  # often no ending
        " thoughts?", " lmk.", " anyone?", " thx.",
        " cc @quality.", " ping me if questions.",
    ]
    text += random.choice(endings)
    return text

def style_email_casual(text: str) -> str:
    """Add a casual email opener."""
    openers = [
        "Hi,", "Hey,", "Hi team,", "Quick note —",
        "Wanted to flag this:", "Just so you know,",
        "Putting this on your radar:", "Small update —",
    ]
    return f"{random.choice(openers)} {text[0].lower() + text[1:]}"

def style_email_formal(text: str) -> str:
    """Add a formal email opener."""
    openers = [
        "Hello,", "Good morning,", "Good afternoon,",
        "For your attention:", "Regarding production quality:",
        "Subject: Quality issue —",
    ]
    return f"{random.choice(openers)} {text}"

def style_verbal(text: str) -> str:
    """Spoken/walkie style openers."""
    openers = [
        "Yeah so,", "OK listen,", "Hey,", "So,",
        "Alright,", "Just to let you know,", "Real quick —",
        "Heads up,",
    ]
    return f"{random.choice(openers)} {text[0].lower() + text[1:]}"

def style_clipboard(text: str) -> str:
    """Short-form clipboard. Remove some words, compress."""
    # Replace some phrases to be more telegraphic
    text = text.replace("We think it's due to", "Cause:")
    text = text.replace("Looks like", "Poss.")
    text = text.replace("We're seeing", "Observed:")
    text = text.replace("Found", "Found:")
    text = text.replace("Noticed", "Noted:")
    # Trim to first 3-4 sentences max
    parts = text.split(".")
    parts = [p.strip() for p in parts if p.strip()][:4]
    return ". ".join(parts) + "."

def style_report(text: str) -> str:
    """Formal report prefix."""
    prefixes = [
        "Quality incident —", "NCR —", "Defect report —",
        "Inspection finding —", "Production alert —", "QC log entry —",
        "Non-conformance —",
    ]
    return f"{random.choice(prefixes)} {text}"

def style_handoff(text: str) -> str:
    """Shift handoff note."""
    shift = random.choice(SHIFTS)
    op = random.choice(OPERATORS)
    openers = [
        f"{op} here, {shift} handoff.",
        f"End of {shift} notes:",
        f"{shift} update from {op}.",
        f"Handing off from {shift} —",
        f"Log entry, {shift}:",
    ]
    return f"{random.choice(openers)} {text}"


STYLE_FNS = [
    (style_raw, 0.15),
    (style_slack, 0.15),
    (style_email_casual, 0.14),
    (style_email_formal, 0.08),
    (style_verbal, 0.13),
    (style_clipboard, 0.10),
    (style_report, 0.12),
    (style_handoff, 0.13),
]


def generate_input(defect_type: str, line: str, part: str, cause: str) -> str:
    """Generate an improved input."""
    base = compose_input(defect_type, line, part, cause)
    styles, weights = zip(*STYLE_FNS)
    style_fn = random.choices(styles, weights=weights, k=1)[0]
    return style_fn(base)


# ============================================================================
# ANALYSIS & VALIDATION
# ============================================================================

def analyze(examples: list[dict], label: str = ""):
    if label:
        print(f"\n{'='*60}")
        print(f"  {label}")
        print(f"{'='*60}")

    sev_words = [
        "low", "medium", "high", "critical", "minor", "cosmetic", "slight",
        "negligible", "moderate", "noticeable", "significant", "concerning",
        "serious", "major", "severe", "substantial", "urgent", "dangerous",
        "safety-related", "show-stopper",
    ]
    sev_leak = sum(1 for ex in examples if any(w in ex["input"].lower() for w in sev_words))
    defect_verbatim = sum(1 for ex in examples if ex["output"]["defect_type"] in ex["input"].lower())

    starts = Counter()
    for ex in examples:
        first_words = " ".join(ex["input"].split()[:3])
        starts[first_words] += 1

    endings = Counter()
    for ex in examples:
        last_sent = ex["input"].rstrip(".").split(".")[-1].strip()
        if len(last_sent) < 60:
            endings[last_sent] += 1

    sev_counts = Counter(ex["output"]["severity"] for ex in examples)
    lengths = [len(ex["input"].split()) for ex in examples]

    print(f"  Total: {len(examples)}")
    print(f"  Severity dist: {dict(sorted(sev_counts.items()))}")
    print(f"  Severity leaking: {sev_leak}/{len(examples)} ({sev_leak/len(examples)*100:.1f}%)")
    print(f"  Defect verbatim: {defect_verbatim}/{len(examples)} ({defect_verbatim/len(examples)*100:.1f}%)")
    print(f"  Unique inputs: {len(set(ex['input'] for ex in examples))}/{len(examples)}")
    print(f"  Input length: min={min(lengths)}, max={max(lengths)}, avg={sum(lengths)/len(lengths):.1f} words")

    print(f"  Top 5 openings:")
    for k, v in starts.most_common(5):
        print(f"    {v:3d}x  \"{k}\"")
    print(f"  Top 5 endings:")
    for k, v in endings.most_common(5):
        print(f"    {v:3d}x  \"{k}\"")

    banned = [
        "Please be advised", "Initial assessment indicates",
        "Awaiting your guidance", "Let me know if you need photos",
        "Happy to discuss further", "Documentation attached",
        "Further analysis is recommended", "Corrective action pending",
    ]
    for pat in banned:
        count = sum(1 for ex in examples if pat in ex["input"])
        if count > 0:
            print(f"  BANNED: \"{pat}\" x{count}")


def main():
    src = Path(__file__).parent / "manufacturing_qa_500.jsonl"
    bak = Path(__file__).parent / "manufacturing_qa_500.jsonl.bak"

    with open(src) as f:
        examples = [json.loads(line) for line in f]

    print(f"Loaded {len(examples)} examples")

    # Load original for BEFORE stats
    if bak.exists():
        with open(bak) as f:
            originals = [json.loads(line) for line in f]
        analyze(originals, "BEFORE (original)")
    else:
        analyze(examples, "BEFORE")
        shutil.copy2(src, bak)
        print(f"\nBackup: {bak}")

    # Rewrite inputs
    seen = set()
    for ex in examples:
        out = ex["output"]
        for _ in range(30):
            new_input = generate_input(
                out["defect_type"],
                out["production_line"],
                out["part"],
                out["probable_cause"],
            )
            if new_input not in seen:
                ex["input"] = new_input
                seen.add(new_input)
                break
        else:
            ex["input"] = new_input + f" Ref QA-{random.randint(10000, 99999)}."
            seen.add(ex["input"])

    analyze(examples, "AFTER")

    # Validate
    required_keys = {"defect_type", "severity", "production_line", "part", "probable_cause", "next_action"}
    valid_severities = {"low", "medium", "high", "critical"}
    errors = []
    for i, ex in enumerate(examples):
        if not isinstance(ex.get("input"), str) or not ex["input"].strip():
            errors.append(f"[{i}] empty input")
        out = ex.get("output", {})
        if set(out.keys()) != required_keys:
            errors.append(f"[{i}] wrong keys: {set(out.keys())}")
        if out.get("severity") not in valid_severities:
            errors.append(f"[{i}] bad severity: {out.get('severity')}")
        for k in required_keys:
            if not out.get(k):
                errors.append(f"[{i}] empty: {k}")

    if errors:
        print(f"\nFAILED ({len(errors)} errors):")
        for e in errors[:20]:
            print(f"  {e}")
        return

    with open(src, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(examples)} to {src}")


if __name__ == "__main__":
    main()
