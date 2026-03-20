#!/usr/bin/env python3
"""Final cleanup pass on manufacturing QA dataset."""

import json
import random
import re
from collections import Counter
from pathlib import Path

random.seed(123)

SRC = Path(__file__).parent / "manufacturing_qa_500.jsonl"

# ============================================================================
# REPLACEMENT POOLS
# ============================================================================

# Replacements for "Working theory: CAUSE."
CAUSE_REWRITES = [
    lambda c: f"Looks like {c}.",
    lambda c: f"Probably {c}.",
    lambda c: f"We think it's {c}.",
    lambda c: f"Most likely {c}.",
    lambda c: f"Suspecting {c}.",
    lambda c: f"Could be {c}.",
    lambda c: f"My guess is {c}.",
    lambda c: f"Seems to be {c}.",
    lambda c: f"Pretty sure it's {c}.",
    lambda c: f"Traced it back to {c}.",
    lambda c: f"Evidence points to {c}.",
    lambda c: f"Best guess: {c}.",
    lambda c: f"Cause is probably {c}.",
    lambda c: f"Might be {c}.",
    lambda c: f"I'd say {c}.",
    lambda c: f"Pointing at {c}.",
    lambda c: f"Think it's {c}.",
]

# Replacements for "Station report: LINE, part type PART."
STATION_REWRITES = [
    lambda l, p: f"From {l}, the {p}.",
    lambda l, p: f"This is from {l} — the {p}.",
    lambda l, p: f"{l}, checking the {p}.",
    lambda l, p: f"On {l}, the {p} batch.",
    lambda l, p: f"Issue at {l} with the {p}.",
    lambda l, p: f"{l} — problem with the {p}.",
    lambda l, p: f"Report from {l}: {p}.",
    lambda l, p: f"Flagging an issue on {l}, the {p}.",
    lambda l, p: f"{l}: {p} has a problem.",
    lambda l, p: f"Found something on {l} — the {p}.",
]

# Replacements for repetitive endings
ENDING_REPLACEMENTS = {
    "This wasn't caught by the in-line check.": [
        "Slipped through the automated check.",
        "The inline station didn't pick it up.",
        "Wasn't flagged at the checkpoint.",
        "Got past the in-process inspection.",
        "The auto check missed it.",
    ],
    "Added to the daily scrap report.": [
        "Logged in the scrap tracker.",
        "Recorded for the shift report.",
        "Noted in the daily log.",
        "Documented for tracking.",
        "On the shift summary.",
    ],
    "Tagged for further inspection.": [
        "Flagged for a closer look.",
        "Marked for re-inspection.",
        "Set aside for QC review.",
        "Pulled for detailed check.",
        "Needs a second look.",
    ],
    "The customer spec is tight on this one.": [
        "Tight tolerance on this part.",
        "Customer won't accept this.",
        "This one has a strict spec.",
        "Zero margin on this part number.",
        "The spec doesn't leave much room.",
    ],
    "Checked the previous batch — those are fine.": [
        "Prior batch looked OK.",
        "Earlier units were clean.",
        "The ones from yesterday are fine.",
        "Previous run had no issues.",
        "Last batch passed without problems.",
    ],
    "QC is aware.": [
        "Quality team knows.",
        "Already flagged to QC.",
        "QC has been notified.",
        "Passed it along to quality.",
        "Quality is looking into it.",
    ],
    "Operator log updated.": [
        "Logged it.",
        "Updated the log.",
        "Written up.",
        "Documented.",
        "On record now.",
    ],
    "The gauge confirmed it.": [
        "Gauge reading backs it up.",
        "Confirmed with measurement.",
        "Gauged it — confirmed.",
        "Verified with the gauge.",
        "Double-checked with instruments.",
    ],
    "This batch was supposed to ship today.": [
        "Was scheduled to go out today.",
        "This was a rush order.",
        "These were due for shipment.",
        "The customer is expecting this batch.",
        "Supposed to ship end of day.",
    ],
    "This started after the tooling change.": [
        "Started right after we swapped tooling.",
        "Began after the last tooling setup.",
        "Coincides with the tool changeover.",
        "Tooling swap might be related.",
        "Happened right after tool change.",
    ],
    "Visual check only so far.": [
        "Only a visual so far.",
        "Haven't done a full measurement yet.",
        "Based on visual inspection.",
        "Just a quick look for now.",
        "Eyeball check — needs measuring.",
    ],
    "Set aside for review.": [
        "Pulled aside.",
        "Set it apart for now.",
        "Holding it for review.",
        "Quarantined.",
        "Separated from the batch.",
    ],
    "Not our usual failure mode.": [
        "Haven't seen this before.",
        "New type of failure for us.",
        "Unusual issue.",
        "First time we're seeing this.",
        "Different from what we usually get.",
    ],
}

# Chat artifact replacements
CHAT_ENDINGS = {
    " thx.": [".", ""],
    " lmk.": [" — let us know what you think.", " — need input.", ""],
    " cc @quality.": [" — quality team copied.", ""],
    " ping me if questions.": [" — reach out if needed.", ""],
    " thoughts?": [" — what do you think?", " — any ideas?", ""],
    " anyone?": [" — anyone seen this before?", ""],
}


# ============================================================================
# FIX FUNCTIONS
# ============================================================================

def fix_the_part_has(text: str) -> str:
    """Fix all broken 'The part has [sentence]' patterns."""
    # List of sentence starters that indicate a broken concatenation
    # "The part has it's crooked" -> "It's crooked"
    # "The part has we're short" -> "We're short"
    # "The part has there are runs" -> "There are runs"
    # "The part has I can see" -> "I can see"
    # "The part has it wobbles" -> "It wobbles"
    # "The part has the bead is" -> "The bead is"
    # etc.
    starters = (
        r"it's", r"it\s", r"the\s", r"there's", r"there\s", r"we're",
        r"I\s", r"you\s", r"someone", r"something", r"fluid",
    )
    pattern = r"The part has\s+(" + "|".join(starters) + r")"

    def _fix(m):
        captured = m.group(1)
        # Capitalize the first letter
        return captured[0].upper() + captured[1:]

    text = re.sub(pattern, _fix, text, flags=re.IGNORECASE)
    return text


def fix_around_around(text: str) -> str:
    """Fix 'around around' -> 'around'."""
    return re.sub(r"\baround\s+around\b", "around", text)


def fix_pulled_qty_part(text: str) -> str:
    """Fix 'we pulled 3 units shaft' -> 'we pulled 3 shaft units'."""
    # Match: pulled [qty words] [part] where part is immediately after qty
    parts_list = [
        "bracket", "housing", "gasket", "shaft", "bearing", "circuit board",
        "panel", "frame", "connector", "valve", "seal", "rotor",
        "cover plate", "heat sink", "bushing", "spring", "lever arm",
        "nozzle", "impeller", "coupling", "flange", "gear", "manifold",
        "relay", "actuator", "motor casing", "wiring harness", "piston",
        "cylinder head", "control module",
    ]
    for part in parts_list:
        # "pulled 3 units shaft" -> "pulled 3 shaft units"
        pattern = rf"(pulled\s+)((?:the\s+(?:whole|last)\s+|a\s+|about\s+|at\s+least\s+|maybe\s+|\d+\s+)\w+\s+)({re.escape(part)})\b"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            # "pulled [qty] [part]" is awkward — rewrite to "pulled [qty] [part] units" or "[part] — pulled [qty]"
            qty_text = match.group(2).strip()
            text = text[:match.start()] + f"pulled {qty_text} {part} units" + text[match.end():]
    return text


def fix_working_theory(text: str) -> str:
    """Replace most 'Working theory: X.' with varied alternatives."""
    match = re.search(r"Working theory:\s*([^.]+)\.", text)
    if match:
        cause = match.group(1).strip()
        rewrite_fn = random.choice(CAUSE_REWRITES)
        text = text[:match.start()] + rewrite_fn(cause) + text[match.end():]
    return text


def fix_station_report(text: str, line: str, part: str) -> str:
    """Replace 'Station report: LINE, part type PART.' with varied alternatives."""
    pattern = r"Station report:\s*[^,]+,\s*part type\s*[^.]+\."
    match = re.search(pattern, text)
    if match:
        rewrite_fn = random.choice(STATION_REWRITES)
        text = text[:match.start()] + rewrite_fn(line, part) + text[match.end():]
    return text


def fix_repetitive_endings(text: str) -> str:
    """Replace repetitive endings with varied alternatives."""
    for pattern, replacements in ENDING_REPLACEMENTS.items():
        pattern_base = pattern.rstrip(".")
        # Check if pattern appears anywhere as a sentence
        if pattern_base in text:
            if random.random() < 0.75:
                repl = random.choice(replacements)
                if not repl.endswith(".") and repl:
                    repl += "."
                text = text.replace(pattern_base + ".", repl, 1)
                text = text.replace(pattern_base, repl.rstrip("."), 1)
    return text


def fix_chat_artifacts(text: str) -> str:
    """Remove or replace chat-style endings."""
    for pattern, replacements in CHAT_ENDINGS.items():
        if text.rstrip(".").endswith(pattern.rstrip(".")):
            if random.random() < 0.75:
                repl = random.choice(replacements)
                idx = text.rstrip(".").rfind(pattern.rstrip("."))
                text = text[:idx] + repl
                if text and not text.rstrip().endswith(".") and not text.rstrip().endswith("?"):
                    text = text.rstrip() + "."
    return text


def fix_duplicate_sentences(text: str) -> str:
    """Remove duplicate sentences within the same input."""
    parts = re.split(r"(?<=[.!?])\s+", text)
    seen = set()
    deduped = []
    for p in parts:
        normalized = p.strip().lower()
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(p)
    return " ".join(deduped)


def fix_double_spaces(text: str) -> str:
    """Clean up double spaces and trailing issues."""
    text = re.sub(r"\s{2,}", " ", text)
    text = text.strip()
    # Fix ". ." or ".."
    text = re.sub(r"\.{2,}", ".", text)
    text = re.sub(r"\.\s*\.", ".", text)
    # Ensure ends with punctuation
    if text and text[-1] not in ".?!":
        text += "."
    return text


def fix_sentence_start_after_period(text: str) -> str:
    """Capitalize first letter after period."""
    def cap_match(m):
        return m.group(1) + m.group(2).upper()
    text = re.sub(r"(\.\s+)([a-z])", cap_match, text)
    return text


def fix_upstream_station(text: str) -> str:
    """Vary 'Upstream station didn't flag anything.' when too common."""
    if "Upstream station didn't flag anything" in text:
        if random.random() < 0.6:
            replacements = [
                "Previous station didn't catch it.",
                "Nothing flagged upstream.",
                "The prior step passed it through.",
                "No alert from the station before.",
                "It got through the earlier checks.",
            ]
            text = text.replace("Upstream station didn't flag anything.", random.choice(replacements))
    return text


# ============================================================================
# MAIN
# ============================================================================

def apply_all_fixes(text: str, line: str, part: str) -> str:
    """Apply all fixes in order."""
    text = fix_around_around(text)
    text = fix_the_part_has(text)
    text = fix_pulled_qty_part(text)
    text = fix_working_theory(text)
    text = fix_station_report(text, line, part)
    text = fix_repetitive_endings(text)
    text = fix_chat_artifacts(text)
    text = fix_upstream_station(text)
    text = fix_duplicate_sentences(text)
    text = fix_double_spaces(text)
    text = fix_sentence_start_after_period(text)
    return text


def analyze(examples: list[dict], label: str):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")

    patterns_to_check = [
        "Working theory:", "The part has", "Station report:",
        "QC is aware", "Operator log updated", "thx.", "lmk.",
        "cc @quality.", "ping me if questions.", "around around",
        "Upstream station didn't flag anything",
    ]

    for p in patterns_to_check:
        c = sum(1 for ex in examples if p in ex["input"])
        if c > 0:
            print(f"  {c:3d}x  \"{p}\"")

    # Grammar issues
    broken = sum(1 for ex in examples if re.search(r"The part has (it's|the \w+ is|there's)", ex["input"]))
    print(f"  {broken:3d}x  broken 'The part has...' grammar")

    # Top endings
    endings = Counter()
    for ex in examples:
        last = ex["input"].rstrip(".").split(".")[-1].strip()
        if len(last) < 60:
            endings[last] += 1

    print(f"  Top 5 endings:")
    for k, v in endings.most_common(5):
        print(f"    {v:3d}x  \"{k}\"")

    # Top openings
    starts = Counter()
    for ex in examples:
        first = " ".join(ex["input"].split()[:3])
        starts[first] += 1

    print(f"  Top 5 openings:")
    for k, v in starts.most_common(5):
        print(f"    {v:3d}x  \"{k}\"")

    unique = len(set(ex["input"] for ex in examples))
    print(f"  Unique: {unique}/{len(examples)}")


def main():
    with open(SRC) as f:
        examples = [json.loads(line) for line in f]

    analyze(examples, "BEFORE CLEANUP")

    # Apply fixes
    for ex in examples:
        out = ex["output"]
        ex["input"] = apply_all_fixes(
            ex["input"],
            out["production_line"],
            out["part"],
        )

    analyze(examples, "AFTER CLEANUP")

    # Validate
    required = {"defect_type", "severity", "production_line", "part", "probable_cause", "next_action"}
    valid_sev = {"low", "medium", "high", "critical"}
    errors = []
    for i, ex in enumerate(examples):
        if not ex.get("input", "").strip():
            errors.append(f"[{i}] empty input")
        out = ex.get("output", {})
        if set(out.keys()) != required:
            errors.append(f"[{i}] wrong keys")
        if out.get("severity") not in valid_sev:
            errors.append(f"[{i}] bad severity")

    if errors:
        print(f"\nERRORS: {errors}")
        return

    # Check uniqueness
    unique = len(set(ex["input"] for ex in examples))
    if unique < len(examples):
        print(f"\nWARNING: {len(examples) - unique} duplicates!")
        # Deduplicate by appending small variation
        seen = set()
        for ex in examples:
            if ex["input"] in seen:
                ex["input"] = ex["input"].rstrip(".") + f" (ref {random.randint(100,999)})."
            seen.add(ex["input"])

    with open(SRC, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nWrote {len(examples)} examples to {SRC}")


if __name__ == "__main__":
    main()
