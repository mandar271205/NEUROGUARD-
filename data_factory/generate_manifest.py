from __future__ import annotations

import argparse
import csv
from pathlib import Path


def label_for_prompt(prompt: str) -> str:
    stress_words = ["tension", "pressure", "deadline", "stress", "peeche", "workload"]
    return "stress" if any(word in prompt.lower() for word in stress_words) else "neutral"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompts", default="data_factory/prompts_hinglish.txt")
    parser.add_argument("--audio-dir", default="data_factory/synth_stress")
    parser.add_argument("--out", default="data_factory/manifest.csv")
    args = parser.parse_args()

    prompts = [line.strip() for line in Path(args.prompts).read_text(encoding="utf-8").splitlines() if line.strip()]
    audio_dir = Path(args.audio_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)

    with Path(args.out).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["file_path", "label", "prompt", "speaker_id"])
        writer.writeheader()
        for index, prompt in enumerate(prompts, start=1):
            label = label_for_prompt(prompt)
            writer.writerow(
                {
                    "file_path": str(audio_dir / f"{label}_{index:04d}.wav"),
                    "label": label,
                    "prompt": prompt,
                    "speaker_id": "synthetic_indian_student",
                }
            )


if __name__ == "__main__":
    main()
