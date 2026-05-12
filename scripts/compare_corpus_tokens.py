"""Compare token volume between the Bible corpus and the ayore.org corpus.

Tokenization: whitespace word count (language-symmetric, no dependencies).

Reads:
  - data/raw/ayoreoorg/aligned_ayoreoorg.json
  - data/raw/bible/bible.json

Writes:
  - data/processed/corpus_token_stats.json
  - markdown table to stdout
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AYOREO_PATH = ROOT / "data" / "raw" / "ayoreoorg" / "aligned_ayoreoorg.json"
BIBLE_PATH = ROOT / "data" / "raw" / "bible" / "bible.json"
OUT_PATH = ROOT / "data" / "processed" / "corpus_token_stats.json"


def count_tokens(text: str | None) -> int:
    if not text:
        return 0
    return len(text.split())


def summarize(entries, label_field: str | None = None):
    """Return per-corpus stats. If label_field is set, also return per-section stats."""
    en_counts: list[int] = []
    ayo_counts: list[int] = []
    per_section: dict[str, dict[str, list[int]]] = defaultdict(
        lambda: {"en": [], "ayo": []}
    )

    for entry in entries:
        en = count_tokens(entry.get("body_en"))
        ayo = count_tokens(entry.get("body_ayo"))
        en_counts.append(en)
        ayo_counts.append(ayo)
        if label_field:
            sec = entry.get(label_field) or "unknown"
            per_section[sec]["en"].append(en)
            per_section[sec]["ayo"].append(ayo)

    def stats(xs: list[int]) -> dict:
        nonzero = [x for x in xs if x > 0]
        return {
            "n_entries": len(xs),
            "n_nonempty": len(nonzero),
            "total_tokens": sum(xs),
            "mean": round(statistics.mean(xs), 1) if xs else 0,
            "median": int(statistics.median(xs)) if xs else 0,
            "max": max(xs) if xs else 0,
        }

    out = {
        "n_entries": len(entries),
        "en": stats(en_counts),
        "ayo": stats(ayo_counts),
        "combined_total": sum(en_counts) + sum(ayo_counts),
    }
    if per_section:
        out["per_section"] = {
            sec: {
                "n_entries": len(d["en"]),
                "en_total": sum(d["en"]),
                "ayo_total": sum(d["ayo"]),
                "combined": sum(d["en"]) + sum(d["ayo"]),
            }
            for sec, d in per_section.items()
        }
    return out


def fmt(n: int) -> str:
    return f"{n:,}"


def print_table(stats: dict) -> None:
    print("\n## Token comparison — whitespace word count\n")
    print("| Corpus | Entries | EN tokens | AYO tokens | Combined | EN:AYO ratio |")
    print("|:---|---:|---:|---:|---:|---:|")
    for name in ("ayoreo_org", "bible"):
        s = stats[name]
        en = s["en"]["total_tokens"]
        ayo = s["ayo"]["total_tokens"]
        combined = s["combined_total"]
        ratio = f"{en / ayo:.2f}" if ayo else "n/a"
        print(
            f"| {name} | {fmt(s['n_entries'])} | {fmt(en)} | {fmt(ayo)} "
            f"| {fmt(combined)} | {ratio} |"
        )

    print("\n### Per-entry distribution\n")
    print("| Corpus | Lang | mean | median | max |")
    print("|:---|:---|---:|---:|---:|")
    for name in ("ayoreo_org", "bible"):
        for lang in ("en", "ayo"):
            s = stats[name][lang]
            print(
                f"| {name} | {lang} | {s['mean']} | {s['median']} | {fmt(s['max'])} |"
            )

    if "per_section" in stats["ayoreo_org"]:
        print("\n### ayore.org by section\n")
        print("| Section | Entries | EN tokens | AYO tokens | Combined |")
        print("|:---|---:|---:|---:|---:|")
        rows = sorted(
            stats["ayoreo_org"]["per_section"].items(),
            key=lambda kv: -kv[1]["combined"],
        )
        for sec, d in rows:
            print(
                f"| {sec} | {d['n_entries']} | {fmt(d['en_total'])} "
                f"| {fmt(d['ayo_total'])} | {fmt(d['combined'])} |"
            )


def main() -> None:
    with AYOREO_PATH.open(encoding="utf-8") as f:
        ayoreo_raw = json.load(f)
    with BIBLE_PATH.open(encoding="utf-8") as f:
        bible_raw = json.load(f)

    ayoreo_entries = list(ayoreo_raw.values())
    bible_entries = list(bible_raw.values())

    stats = {
        "ayoreo_org": summarize(ayoreo_entries, label_field="type"),
        "bible": summarize(bible_entries, label_field="section"),
        "tokenizer": "whitespace_split",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    print_table(stats)
    print(f"\nWrote {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
