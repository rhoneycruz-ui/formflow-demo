"""Generate deterministic public FormFlow assets and test Ground Truth."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from formflow.sample_factory import SampleKind, render_sample  # noqa: E402
from formflow.template import render_blank_form  # noqa: E402


def _serialize_key(key) -> str:
    return f"{key.product_id}.{key.field_name.value}"


def main() -> None:
    template_dir = ROOT / "assets" / "template"
    sample_dir = ROOT / "assets" / "samples"
    fixture_dir = ROOT / "tests" / "fixtures"
    template_dir.mkdir(parents=True, exist_ok=True)
    sample_dir.mkdir(parents=True, exist_ok=True)
    fixture_dir.mkdir(parents=True, exist_ok=True)

    render_blank_form().save(template_dir / "formflow-blank.png", optimize=True)
    fixture: dict[str, object] = {}
    seeds = {SampleKind.CLEAN: 101, SampleKind.NOISY: 202, SampleKind.REVIEW: 303}
    for kind, seed in seeds.items():
        sample = render_sample(kind, seed=seed)
        sample.image.save(sample_dir / f"{kind.value}.png", optimize=True)
        fixture[kind.value] = {
            "seed": seed,
            "fields": {_serialize_key(key): value for key, value in sample.ground_truth.items()},
            "ambiguous": [_serialize_key(key) for key in sample.ambiguous_keys],
        }

    (fixture_dir / "sample_ground_truth.json").write_text(
        json.dumps(fixture, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
