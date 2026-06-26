"""Download a subset of HotpotQA (500 examples) and write them to data/hotpotqa/.

This module downloads 500 examples from the HotpotQA fullwiki validation split
using the Hugging Face datasets library. It writes:
- Context documents as individual text files (sample_XXXX.txt)
- Question-answer pairs to qa_pairs.json for benchmarking

Usage:
    python data/download_hotpotqa.py
"""
import json
from pathlib import Path
from datasets import load_dataset


def download_and_save_hotpotqa(output_dir: Path, num_samples: int = 500) -> None:
    """Download HotpotQA samples and save contexts and Q&A pairs.

    Downloads the specified number of samples from the HotpotQA fullwiki
    validation split. Writes context documents as text files and Q&A pairs
    as JSON.

    Args:
        output_dir: Path to directory where samples will be saved.
        num_samples: Number of samples to download (default: 500).

    Returns:
        None. Prints confirmation message upon completion.
    """
    output_dir.mkdir(exist_ok=True)

    ds = load_dataset("hotpotqa/hotpot_qa", "fullwiki", split="validation", streaming=True)
    samples = []
    for i, row in enumerate(ds):
        if i >= num_samples:
            break
        samples.append(row)

    # Write contexts as text files
    for i, sample in enumerate(samples):
        context_parts = []
        for title, sentences in zip(sample["context"]["title"], sample["context"]["sentences"]):
            context_parts.append(f"# {title}\n" + " ".join(sentences))
        text = "\n\n".join(context_parts)
        (output_dir / f"sample_{i:04d}.txt").write_text(text, encoding="utf-8")

    # Write Q&A pairs for benchmark
    qa_pairs = [{"question": s["question"], "answer": s["answer"]} for s in samples]
    (output_dir / "qa_pairs.json").write_text(
        json.dumps(qa_pairs, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"✓ {len(samples)} samples écrits dans {output_dir}")


if __name__ == "__main__":
    OUT = Path(__file__).parent / "hotpotqa"
    download_and_save_hotpotqa(OUT)
