#!/usr/bin/env python3
"""Generate synthetic manufacturing QA dataset for SFT fine-tuning."""

import json
import random
from collections import Counter
from pathlib import Path

# ============================================================================
# DATA POOLS
# ============================================================================

DEFECT_TYPES = [
    "scratch", "dent", "crack", "misalignment", "wrong label",
    "missing component", "loose fastener", "contamination", "leak",
    "welding defect", "paint defect", "dimension out of tolerance",
    "packaging damage", "sensor failure", "assembly error",
]

SEVERITIES = {"low": 100, "medium": 175, "high": 150, "critical": 75}

PRODUCTION_LINES = [
    "Line 1", "Line 2", "Line 3", "Line A", "Line B",
    "Assembly Line", "Packaging Line",
]

PARTS = [
    "bracket", "housing", "gasket", "shaft", "bearing", "circuit board",
    "panel", "frame", "connector", "valve", "seal", "rotor",
    "cover plate", "heat sink", "bushing", "spring", "lever arm",
    "nozzle", "impeller", "coupling", "flange", "gear", "manifold",
    "relay", "actuator", "motor casing", "wiring harness", "piston",
    "cylinder head", "control module",
]

OPERATORS = [
    "Mike", "Sarah", "James", "Linda", "Carlos", "Priya", "Tom",
    "Angela", "Wei", "David", "Maria", "Steve", "Rachel", "Omar", "Kim",
]

SHIFTS = ["morning shift", "afternoon shift", "night shift"]

CONTEXT_PHRASES = [
    "during routine inspection",
    "after customer complaint",
    "spotted by QC team",
    "during end-of-line testing",
    "noticed by the operator on duty",
    "found during preventive maintenance",
    "flagged by automated vision system",
    "caught before shipment",
    "reported by downstream station",
    "identified during rework",
    "discovered during audit",
    "seen after changeover",
    "observed during first article inspection",
    "detected by incoming quality check",
]

# Causes mapped per defect type
CAUSES = {
    "scratch": [
        "improper handling during transport",
        "worn conveyor belt surface",
        "debris on tooling fixture",
        "operator mishandling",
        "contact with adjacent parts on the line",
        "packaging material rubbing during transit",
    ],
    "dent": [
        "dropped during transfer between stations",
        "impact from robotic arm misalignment",
        "stacking pressure in storage bin",
        "forklift collision with pallet",
        "tool strike during assembly",
        "compressed air hose impact",
    ],
    "crack": [
        "material fatigue from thermal cycling",
        "excessive torque during fastening",
        "defective raw material batch",
        "stress concentration at sharp corner",
        "vibration during transport",
        "improper heat treatment",
    ],
    "misalignment": [
        "worn fixture locating pins",
        "incorrect jig setup after changeover",
        "thermal expansion of mounting plate",
        "operator skipped alignment step",
        "calibration drift on positioning system",
        "loose guide rail bolts",
    ],
    "wrong label": [
        "label printer loaded with wrong roll",
        "operator selected wrong SKU in system",
        "database mapping error between part number and label",
        "leftover labels from previous batch run",
        "barcode scanner misread during printing",
        "label template not updated after engineering change",
    ],
    "missing component": [
        "feeder bin ran empty unnoticed",
        "component not included in kit",
        "operator skipped step in assembly sequence",
        "pick-and-place nozzle failed to grip part",
        "BOM discrepancy with physical kit",
        "supplier short-shipped the order",
    ],
    "loose fastener": [
        "torque gun not calibrated",
        "wrong fastener length used",
        "cross-threaded bolt",
        "operator did not complete tightening sequence",
        "vibration loosened connection over time",
        "stripped thread in receiving hole",
    ],
    "contamination": [
        "oil leak from overhead hydraulic line",
        "dust ingress from nearby grinding station",
        "operator gloves contaminated with residue",
        "cleaning solvent not fully evaporated",
        "foreign particle from raw material supplier",
        "coolant splash from adjacent machine",
    ],
    "leak": [
        "cracked O-ring seal",
        "improper gasket seating",
        "weld porosity in joint",
        "overtightened fitting caused deformation",
        "thermal cycling degraded sealant",
        "wrong sealant type applied",
    ],
    "welding defect": [
        "incorrect welding parameters set",
        "shielding gas flow too low",
        "contaminated filler material",
        "operator fatigue on manual weld",
        "fixture misalignment shifted joint position",
        "worn electrode tip",
    ],
    "paint defect": [
        "paint viscosity out of spec",
        "dust contamination in spray booth",
        "incorrect spray gun distance",
        "surface not properly degreased before painting",
        "temperature spike in curing oven",
        "expired paint batch used",
    ],
    "dimension out of tolerance": [
        "tool wear on CNC cutter",
        "thermal drift in machine spindle",
        "incorrect offset entered by operator",
        "material hardness variation from supplier",
        "fixture clamp slipped during machining",
        "programming error in G-code",
    ],
    "packaging damage": [
        "insufficient cushioning material",
        "box size too small for part",
        "rough handling by logistics team",
        "stacking weight exceeded box rating",
        "moisture damage from warehouse leak",
        "shrink wrap machine overheated material",
    ],
    "sensor failure": [
        "sensor wiring harness damaged during installation",
        "electromagnetic interference from nearby motor",
        "sensor exceeded rated operating temperature",
        "moisture ingress into sensor housing",
        "calibration not performed after replacement",
        "defective sensor from supplier batch",
    ],
    "assembly error": [
        "work instruction not followed",
        "components installed in wrong order",
        "parts from two different revisions mixed",
        "operator not trained on updated procedure",
        "incorrect sub-assembly pulled from staging area",
        "missing verification step in process",
    ],
}

# Actions mapped per severity
ACTIONS = {
    "low": [
        "log defect and continue production",
        "notify quality team for monitoring",
        "add to weekly review list",
        "mark unit for rework at end of shift",
        "document and track for trend analysis",
        "apply cosmetic touch-up and release",
    ],
    "medium": [
        "quarantine affected batch for inspection",
        "escalate to shift supervisor",
        "perform root cause analysis",
        "rework affected units before shipment",
        "update control plan with new check",
        "retrain operator on procedure",
        "adjust process parameters and re-verify",
    ],
    "high": [
        "stop production on affected line",
        "issue non-conformance report",
        "initiate 8D corrective action",
        "recall affected batch from warehouse",
        "escalate to plant manager immediately",
        "perform 100% inspection of remaining stock",
        "contact supplier for material investigation",
    ],
    "critical": [
        "halt all production immediately",
        "issue customer notification and containment plan",
        "initiate product recall procedure",
        "convene emergency quality review board",
        "file regulatory incident report",
        "engage third-party inspection team",
        "lock affected inventory in ERP system",
    ],
}

# Severity descriptors for natural language
SEVERITY_WORDS = {
    "low": ["minor", "cosmetic", "slight", "small", "negligible"],
    "medium": ["moderate", "noticeable", "significant", "concerning"],
    "high": ["serious", "major", "severe", "substantial"],
    "critical": ["critical", "urgent", "dangerous", "safety-related", "show-stopper"],
}

# ============================================================================
# TEMPLATE ENGINE
# ============================================================================

def _defect_synonym(defect_type: str) -> str:
    """Return a natural-language phrasing for the defect type."""
    synonyms = {
        "scratch": ["scratch", "surface scratch", "scuff mark", "abrasion"],
        "dent": ["dent", "indentation", "ding", "deformation"],
        "crack": ["crack", "fracture", "hairline crack", "split"],
        "misalignment": ["misalignment", "alignment issue", "offset", "positioning error"],
        "wrong label": ["wrong label", "mislabel", "labeling error", "incorrect label"],
        "missing component": ["missing component", "missing part", "absent component", "omitted part"],
        "loose fastener": ["loose fastener", "loose bolt", "untightened screw", "loose connection"],
        "contamination": ["contamination", "foreign material", "debris", "residue"],
        "leak": ["leak", "seepage", "fluid leak", "drip"],
        "welding defect": ["welding defect", "weld flaw", "poor weld", "weld porosity"],
        "paint defect": ["paint defect", "coating flaw", "paint run", "uneven coating"],
        "dimension out of tolerance": ["dimension out of tolerance", "out-of-spec measurement", "dimensional deviation", "size variance"],
        "packaging damage": ["packaging damage", "damaged packaging", "crushed box", "torn wrapping"],
        "sensor failure": ["sensor failure", "sensor malfunction", "faulty sensor reading", "sensor error"],
        "assembly error": ["assembly error", "assembly mistake", "incorrect assembly", "build error"],
    }
    return random.choice(synonyms.get(defect_type, [defect_type]))


def _severity_word(severity: str) -> str:
    return random.choice(SEVERITY_WORDS[severity])


def _maybe(text: str, prob: float = 0.5) -> str:
    """Return text with given probability, else empty string."""
    return text if random.random() < prob else ""


def operator_note(defect_type: str, severity: str, line: str, part: str, cause: str) -> str:
    """Generate operator-style short note."""
    defect = _defect_synonym(defect_type)
    sev = _severity_word(severity)
    ctx = random.choice(CONTEXT_PHRASES)
    op = random.choice(OPERATORS)
    shift = random.choice(SHIFTS)

    templates = [
        # Template 1 - direct observation
        lambda: " ".join(filter(None, [
            f"Found a {defect} on the {part} at {line}.",
            f"Looks like {cause}.",
            _maybe(f"Severity seems {sev}.", 0.6),
            _maybe(f"Flagged for review.", 0.4),
        ])),
        # Template 2 - shift handoff style
        lambda: " ".join(filter(None, [
            f"{op} here, {shift} update.",
            f"We spotted a {defect} on a {part} coming off {line}.",
            f"Probably caused by {cause}.",
            _maybe(f"Marking this as {sev}.", 0.5),
        ])),
        # Template 3 - quick flag
        lambda: " ".join(filter(None, [
            f"Heads up — {defect} detected on {part}, {line}.",
            _maybe(f"Noticed {ctx}.", 0.7),
            f"Suspect {cause}.",
            _maybe(f"Doesn't look too bad but flagging anyway.", 0.3) if severity == "low" else _maybe(f"This one looks {sev}.", 0.6),
        ])),
        # Template 4 - matter of fact
        lambda: " ".join(filter(None, [
            f"{part} from {line} has a {defect}.",
            f"Root cause is likely {cause}.",
            _maybe(f"Found {ctx}.", 0.5),
            _maybe(f"Tagging as {sev} priority.", 0.4),
        ])),
        # Template 5 - observation first
        lambda: " ".join(filter(None, [
            f"During today's {shift}, I noticed an issue on {line}.",
            f"The {part} shows a clear {defect}.",
            _maybe(f"We think it's due to {cause}.", 0.7),
            _maybe(f"Impact assessed as {sev}.", 0.5),
        ])),
        # Template 6 - concise
        lambda: " ".join(filter(None, [
            f"{defect.capitalize()} on {part} — {line}.",
            f"Cause: {cause}.",
            _maybe(f"Severity: {sev}.", 0.6),
        ])),
        # Template 7 - detailed
        lambda: " ".join(filter(None, [
            f"Reporting a {sev} issue {ctx} on {line}.",
            f"A {defect} was found on the {part}.",
            f"Best guess is {cause}.",
            _maybe(f"Several units affected.", 0.3),
            _maybe(f"Needs attention.", 0.4),
        ])),
    ]
    return random.choice(templates)()


def email_style(defect_type: str, severity: str, line: str, part: str, cause: str) -> str:
    """Generate email-style incident description."""
    defect = _defect_synonym(defect_type)
    sev = _severity_word(severity)
    ctx = random.choice(CONTEXT_PHRASES)
    op = random.choice(OPERATORS)

    templates = [
        # Template 1 - team notification
        lambda: " ".join(filter(None, [
            f"Hi team, just wanted to flag an issue we noticed on {line}.",
            f"The {part} shows signs of {defect}.",
            _maybe(f"This was {ctx}.", 0.6),
            f"We believe the cause is {cause}.",
            _maybe(f"I'd rate this as {sev}.", 0.5),
        ])),
        # Template 2 - escalation
        lambda: " ".join(filter(None, [
            f"Quick update from {line} — we've got a {sev} defect to report.",
            f"{op} found a {defect} on a {part}.",
            f"Likely due to {cause}.",
            _maybe(f"Please advise on next steps.", 0.5),
        ])),
        # Template 3 - FYI
        lambda: " ".join(filter(None, [
            f"FYI — {ctx}, we identified a {defect} affecting the {part} on {line}.",
            f"The probable cause is {cause}.",
            _maybe(f"This is a {sev} issue that needs attention.", 0.6),
            _maybe(f"Let me know if you need photos.", 0.3),
        ])),
        # Template 4 - follow-up
        lambda: " ".join(filter(None, [
            f"Following up on the {part} issue from {line}.",
            f"Confirmed it's a {defect}, most likely from {cause}.",
            _maybe(f"Assessed as {sev} severity.", 0.5),
            _maybe(f"Happy to discuss further.", 0.3),
        ])),
        # Template 5 - brief ping
        lambda: " ".join(filter(None, [
            f"Hey, {op} just reported a problem on {line}.",
            f"There's a {defect} on the {part} that came through.",
            f"Thinking it might be {cause}.",
            _maybe(f"Seems {sev} to me — can someone confirm?", 0.6),
        ])),
        # Template 6 - formal
        lambda: " ".join(filter(None, [
            f"Please be advised that a {defect} has been identified on {part} produced at {line}.",
            f"Initial assessment indicates {cause} as the probable root cause.",
            _maybe(f"Severity has been classified as {sev}.", 0.6),
            _maybe(f"Awaiting your guidance on disposition.", 0.4),
        ])),
    ]
    return random.choice(templates)()


def report_style(defect_type: str, severity: str, line: str, part: str, cause: str) -> str:
    """Generate formal incident report style."""
    defect = _defect_synonym(defect_type)
    sev = _severity_word(severity)
    ctx = random.choice(CONTEXT_PHRASES)
    shift = random.choice(SHIFTS)

    templates = [
        # Template 1 - standard report
        lambda: " ".join(filter(None, [
            f"Incident Report — {line}.",
            f"A {defect} was identified on the {part} {ctx}.",
            f"Root cause appears to be {cause}.",
            f"Severity assessed as {sev}.",
        ])),
        # Template 2 - structured
        lambda: " ".join(filter(None, [
            f"Quality incident logged for {line}, {shift}.",
            f"Defect: {defect} on {part}.",
            f"Probable cause: {cause}.",
            _maybe(f"Classification: {sev}.", 0.7),
            _maybe(f"Corrective action pending.", 0.4),
        ])),
        # Template 3 - narrative
        lambda: " ".join(filter(None, [
            f"During the {shift} on {line}, a {sev} quality issue was discovered.",
            f"The {part} exhibited a {defect}.",
            f"Investigation points to {cause} as the most likely factor.",
            _maybe(f"Further analysis is recommended.", 0.4),
        ])),
        # Template 4 - NCR style
        lambda: " ".join(filter(None, [
            f"Non-conformance detected at {line}.",
            f"Part affected: {part}.",
            f"Nature of defect: {defect}.",
            f"Suspected cause: {cause}.",
            _maybe(f"Priority level: {sev}.", 0.6),
        ])),
        # Template 5 - summary
        lambda: " ".join(filter(None, [
            f"Summary of incident on {line}: {defect} found on {part} {ctx}.",
            f"Analysis suggests {cause}.",
            _maybe(f"Impact rated {sev}.", 0.5),
            _maybe(f"Documentation attached.", 0.2),
        ])),
        # Template 6 - audit finding
        lambda: " ".join(filter(None, [
            f"Audit finding from {line}.",
            f"A {part} was found with {defect} {ctx}.",
            f"Contributing factor identified as {cause}.",
            _maybe(f"This represents a {sev} risk.", 0.6),
            _maybe(f"Immediate containment recommended." if severity in ("high", "critical") else "", 0.5),
        ])),
    ]
    return random.choice(templates)()


STYLE_FUNCTIONS = [operator_note, email_style, report_style]


def generate_input(defect_type: str, severity: str, line: str, part: str, cause: str) -> str:
    """Generate a natural-language incident description."""
    style_fn = random.choice(STYLE_FUNCTIONS)
    return style_fn(defect_type, severity, line, part, cause)


# ============================================================================
# GENERATOR
# ============================================================================

def generate_example(defect_type: str, severity: str) -> dict:
    """Generate a single training example."""
    line = random.choice(PRODUCTION_LINES)
    part = random.choice(PARTS)
    cause = random.choice(CAUSES[defect_type])
    action = random.choice(ACTIONS[severity])

    text = generate_input(defect_type, severity, line, part, cause)

    return {
        "input": text,
        "output": {
            "defect_type": defect_type,
            "severity": severity,
            "production_line": line,
            "part": part,
            "probable_cause": cause,
            "next_action": action,
        },
    }


def generate_dataset(n: int = 500, seed: int = 42) -> list[dict]:
    """Generate the full dataset with correct severity distribution."""
    random.seed(seed)

    # Build severity list with exact distribution
    severity_list = []
    for sev, count in SEVERITIES.items():
        severity_list.extend([sev] * count)

    assert len(severity_list) == n, f"Expected {n}, got {len(severity_list)}"
    random.shuffle(severity_list)

    # Assign defect types uniformly across all examples
    defect_cycle = DEFECT_TYPES * (n // len(DEFECT_TYPES) + 1)
    random.shuffle(defect_cycle)
    defect_list = defect_cycle[:n]

    examples = []
    seen_inputs = set()

    for i in range(n):
        # Retry up to 10 times to avoid duplicate inputs
        for _ in range(10):
            ex = generate_example(defect_list[i], severity_list[i])
            if ex["input"] not in seen_inputs:
                seen_inputs.add(ex["input"])
                examples.append(ex)
                break
        else:
            # Force uniqueness by appending batch ref
            ex["input"] += f" Ref: QA-{random.randint(10000, 99999)}."
            seen_inputs.add(ex["input"])
            examples.append(ex)

    return examples


# ============================================================================
# VALIDATION
# ============================================================================

VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_LINES = set(PRODUCTION_LINES)
REQUIRED_OUTPUT_KEYS = {"defect_type", "severity", "production_line", "part", "probable_cause", "next_action"}


def validate_example(ex: dict, idx: int) -> list[str]:
    """Validate a single example, return list of errors."""
    errors = []
    if not isinstance(ex.get("input"), str) or not ex["input"].strip():
        errors.append(f"[{idx}] input is empty or not a string")
    out = ex.get("output", {})
    if set(out.keys()) != REQUIRED_OUTPUT_KEYS:
        errors.append(f"[{idx}] output keys mismatch: {set(out.keys())}")
    if out.get("severity") not in VALID_SEVERITIES:
        errors.append(f"[{idx}] invalid severity: {out.get('severity')}")
    if out.get("production_line") not in VALID_LINES:
        errors.append(f"[{idx}] invalid production_line: {out.get('production_line')}")
    for k in REQUIRED_OUTPUT_KEYS:
        v = out.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            errors.append(f"[{idx}] field '{k}' is null or empty")
    return errors


def validate_dataset(examples: list[dict]) -> bool:
    """Validate full dataset. Returns True if all checks pass."""
    all_errors = []
    for i, ex in enumerate(examples):
        all_errors.extend(validate_example(ex, i))

    if all_errors:
        print("VALIDATION ERRORS:")
        for e in all_errors:
            print(f"  {e}")
        return False

    # Distribution check
    sev_counts = Counter(ex["output"]["severity"] for ex in examples)
    defect_counts = Counter(ex["output"]["defect_type"] for ex in examples)
    line_counts = Counter(ex["output"]["production_line"] for ex in examples)
    unique_inputs = len(set(ex["input"] for ex in examples))

    print(f"Generated {len(examples)} examples")
    print(f"Severity distribution: {', '.join(f'{k}={v} ({v/len(examples)*100:.1f}%)' for k, v in sorted(sev_counts.items()))}")
    print(f"Defect types covered: {len(defect_counts)}/{len(DEFECT_TYPES)}")
    print(f"Production lines used: {len(line_counts)}/{len(PRODUCTION_LINES)}")
    print(f"Unique inputs: {unique_inputs}/{len(examples)}")

    if unique_inputs < len(examples):
        print(f"WARNING: {len(examples) - unique_inputs} duplicate inputs found")
        return False

    return True


# ============================================================================
# MAIN
# ============================================================================

def main():
    examples = generate_dataset(500, seed=42)
    ok = validate_dataset(examples)
    if not ok:
        print("\nDataset validation FAILED. Aborting.")
        return

    out_path = Path(__file__).parent / "manufacturing_qa_500.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    print(f"\nOutput: {out_path}")


if __name__ == "__main__":
    main()
