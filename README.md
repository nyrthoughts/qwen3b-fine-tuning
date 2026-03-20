# Qwen3-8B SFT — Manufacturing Quality Incidents

Fine-tune [Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B) to extract structured JSON from short manufacturing incident reports using supervised fine-tuning (SFT) with LoRA.

## Task

**Input:** A short paragraph describing a manufacturing quality incident (2-5 sentences, English).

**Output:** A strict JSON object with 6 fields:

```json
{
  "defect_type": "crack",
  "severity": "high",
  "production_line": "Line 2",
  "part": "housing",
  "probable_cause": "material fatigue from thermal cycling",
  "next_action": "stop production on affected line"
}
```

## Dataset

500 synthetic examples in JSONL format, built through a 3-step pipeline:

| Script | Role |
|---|---|
| `generate_dataset.py` | Initial generation with template engine, severity distribution, and validation |
| `improve_dataset.py` | Rewrites inputs using 6 writing styles and composable sentence fragments |
| `cleanup_dataset.py` | Final grammar fixes, pattern reduction, and deduplication |

**Severity distribution:** low 20%, medium 35%, high 30%, critical 15%

**15 defect types:** scratch, dent, crack, misalignment, wrong label, missing component, loose fastener, contamination, leak, welding defect, paint defect, dimension out of tolerance, packaging damage, sensor failure, assembly error.

## Training

The notebook `qwen3_8b_sft.ipynb` runs on Google Colab (T4/A100) and covers:

- 4-bit quantized model loading via [Unsloth](https://github.com/unslothai/unsloth)
- LoRA adapter setup (r=16, all attention + MLP projections)
- SFT with [TRL](https://github.com/huggingface/trl) SFTTrainer (60 steps, lr=2e-4, batch=2, grad_accum=4)
- Baseline vs fine-tuned evaluation (JSON validity, field accuracy, severity match)
- LoRA adapter export as zip

## Quick Start

**Generate the dataset:**

```bash
python generate_dataset.py      # → manufacturing_qa_500.jsonl (raw)
python improve_dataset.py       # → rewrites inputs for variety
python cleanup_dataset.py       # → final quality pass
```

**Fine-tune:** Open `qwen3_8b_sft.ipynb` in Colab, upload `manufacturing_qa_500.jsonl`, and run all cells.

## Files

```
├── generate_dataset.py          # Template-based dataset generator
├── improve_dataset.py           # Input rewriter (6 styles, composable blocks)
├── cleanup_dataset.py           # Grammar/pattern cleanup pass
├── manufacturing_qa_500.jsonl   # Final dataset (500 examples)
└── qwen3_8b_sft.ipynb           # Colab training notebook
```

## License

MIT
