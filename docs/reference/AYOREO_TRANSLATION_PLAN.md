# Ayoreo–English Translation Pipeline (LoRA + Hybrid Inference)
- status: in-progress
- type: plan
- id: ayoreo_translation
- description: End-to-end plan for building a bidirectional English↔Ayoreo machine translation system using NLLB-200 as the base, two-stage LoRA fine-tuning over a mixed Bible + folk-story corpus, an active-learning annotation tool driven by a trilingual researcher, and a hybrid RAG-refinement inference layer designed to mitigate Bible-translationese register bias.
- label: [planning, backend]
- injection: informational
- volatility: evolving
- owner: researcher
- estimate: 10w
- priority: high
- last_checked: 2026-05-12
<!-- content -->

This is **revision 2** of the plan, written after a data audit and after confirming a native-speaker researcher is available to participate in the workflow. It supersedes revision 1 but preserves all stable IDs so any prior references remain valid. Substantive changes from v1 are summarized in the "What changed from v1" section below.

The system translates between English and **Ayoreo** (Zamucoan family; spoken by ~4,500 people across Bolivia and Paraguay). Ayoreo is functionally absent from mainstream LLM pretraining corpora, so the core technical risk is **representation cold-start**. A second, equally important risk surfaced during the data audit: roughly 89% of available Ayoreo training material comes from a Bible translation produced by a non-native English speaker, which carries a measurable translationese fingerprint. The plan is structured to address both risks: NLLB-200 as the base model gives us a multilingual representation foundation; a two-stage training schedule plus a researcher-in-the-loop annotation app gives us a path to escape Bible register.

**Data Snapshot (2026-05-12)**

| Corpus | Pairs | EN tokens (ws) | AYO tokens (ws) | EN:AYO | Notes |
|---|---:|---:|---:|---:|---|
| Bible | 20,324 verse pairs | 487,558 | 763,889 | 0.64 | 759 chapters scraped; 261 with explicit `alignment_map`, rest 1:1; 105 EN verses with no AYO counterpart (dropped); EN→AY by English-speaker translator |
| Folk stories (ayore.org) | 8,156 paragraph pairs | 121,563 | 89,180 | 1.36 | 130 of 132 stories paired; 114 with LLM-produced `alignment_map`; 2 AYO-only stories diverted to monolingual pool; data not yet fully cleaned |
| Dictionary | TBD | TBD | TBD | TBD | Not yet acquired; integration points defined below |

By token count, the Bible accounts for ~89% of available Ayoreo training material. By pair count, ~71%. The disparity matters because per-token gradient signal dominates training, not per-pair sampling frequency.

**Findings and Design Decisions**

**Translationese in the Bible corpus is confirmed.** The EN:AYO whitespace token ratio of 0.64 (Ayoreo uses 57% more words than the English source) is the opposite of what an agglutinative language should produce against an analytic source. The folk stories' ratio of 1.36 — Ayoreo using fewer words than English, as expected — shows the same metric on linguistically natural Ayoreo. The 2.1x ratio gap is large enough to survive any reasonable noise correction for uncleaned folk-story data, so we treat this as a confirmed property of the Bible translation: it is analytic where natural Ayoreo would be synthetic, a classic L2-translation fingerprint. Practical consequence: training on the Bible alone would produce a model that generates translationese Ayoreo. We compensate via training-mix weighting, source tags, a mandatory native-register fine-tune (Stage 2), and an annotation app for direct naturalness corrections.

**Two-stage training is necessary, not optional.** With 89% of AYO tokens being scripture, simple oversampling of folk stories cannot rebalance the gradient signal — a 6x sampling weight on folk stories still leaves the per-batch AYO loss heavily Bible-dominated. We need an isolated Stage 2 phase where loss is computed exclusively on native-speaker Ayoreo to actually shift the output distribution. This was an option in v1; in v2 it is required.

**Source tags become attractive.** Given the register split, prefixing each training example with `<scripture>`, `<narrative>`, or `<lexical>` gives the model an explicit register knob at inference time. With ~28k+ pairs, there is enough data for tag conditioning to take hold reliably.**Test splits are by book / by story, never random verse-level.** The Bible's repeated proper nouns and parallel passages, and the folk stories' within-story vocabulary cohesion, mean random verse-level splits would massively inflate test metrics. Whole-book and whole-story holdouts are the only honest design.

**The trilingual researcher in the loop changes the trajectory.** Phase 5's human evaluation is now staffed. Beyond that, the researcher unlocks active data generation, naturalness corrections of Bible pairs, alignment auditing, and Spanish-pivot workflows — captured in the new Phase A.

**What changed from v1**

- New Phase A (annotation tool + active data generation), inserted after Phase 0 — runs in parallel with the modeling phases.
- Phase 0 partially reclassified as done/in-progress to reflect actual state.
- Phase 0.6 added: alignment audit for the 114 LLM-aligned folk stories.
- Phase 4 restructured into Stage-1 and Stage-2 training (4.4 / 4.5).
- Phase 4.2 updated: starting rank bumped from 8 to 16; MLP projections in `target_modules` from the start; source-tag prefixes added to training data.
- Phase 4.3 added: explicit training-mix weighting scheme.
- Phase 5.2 updated: human rubric now four-dimensional (adequacy, fluency, terminology, **naturalness**), with the researcher as designated evaluator.
- Phase 3 (continued pre-training) un-deprioritized given the value of monolingual native-speaker Ayoreo and the 2 AYO-only stories.
- Phase 6 updated: Spanish pivot pathway added to the refinement layer.
- Dictionary references throughout updated to "if available" rather than assumed.

## Phase 0 — Data Foundation
- status: in-progress
- type: task
- id: ayoreo_translation.data
- owner: researcher
- estimate: 2w
<!-- content -->

Most data acquisition is done; remaining work is normalization, filtering, test-set construction, and alignment audit. The Bible and folk-story corpora are sized and characterized (see Data Snapshot). The dictionary is not yet available; if acquired during the project it slots into training and the inference-time terminology lookup with no plan restructuring.

### 0.1 Source Inventory and Cataloging
- status: done
- type: task
- id: ayoreo_translation.data.inventory
- owner: researcher
- estimate: 3d
<!-- content -->

Completed during the data audit summarized in the Data Snapshot. `data/sources.csv` lists the Bible and ayore.org corpora with provenance, alignment status, and token counts. Add the dictionary as a third row when/if acquired.

### 0.2 Parallel Corpus Construction
- status: done
- type: task
- id: ayoreo_translation.data.parallel_corpus
- owner: researcher
- estimate: 5d
- blocked_by: [ayoreo_translation.data.inventory]
<!-- content -->

Completed: `data/parallel.jsonl` contains 20,324 Bible verse pairs and 8,156 folk-story paragraph pairs. The 2 AYO-only folk stories are written to `data/monolingual_ay.txt` for Phase 3 pretraining instead. Schema:

```python
# data/parallel.jsonl — UTF-8, NFC-normalized
{"id": "bible-mat-5-3",   "src": "bible",      "en": "...", "ay": "...", "alignment": "explicit"}
{"id": "ayore-story-12-3", "src": "folk_story", "en": "...", "ay": "...", "alignment": "llm"}
```

The `src` field is the basis for both per-source evaluation breakdowns and the training-mix weighting in Phase 4.3.

### 0.3 Orthographic Normalization
- status: in-progress
- type: task
- id: ayoreo_translation.data.normalize
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.data.parallel_corpus]
<!-- content -->

Canonical normalization plus orthographic-convention selection. Bible and folk-story sources may use different conventions for tilde, vowel length, and glottal stops; pick one and normalize all sources.

```python
import unicodedata

def normalize_ayoreo(text: str) -> str:
    """
    Canonical normalization for Ayoreo text.
    NFC composition handles cases where 'ñ' is encoded as 'n' + combining tilde,
    which would otherwise tokenize as different tokens than the single-char form.
    """
    return unicodedata.normalize("NFC", text).strip()
```

Document every variant-to-canonical mapping in `data/orthography_rules.md` (separate `reference` document) with a one-line rationale per rule. The researcher in Phase A is the right person to validate these conventions against native intuition once the app is online.

### 0.4 Quality Filtering and Deduplication
- status: todo
- type: task
- id: ayoreo_translation.data.filter
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.data.normalize]
<!-- content -->

Three mechanical filters plus a manual sample audit.

```python
def length_ratio_ok(en: str, ay: str,
                    low: float = 0.3, high: float = 3.0) -> bool:
    """
    Reject pairs with suspicious word-count ratios — usually misalignments.
    Note: folk-story paragraphs naturally have wider ratios than verses,
    so consider per-source thresholds if many valid paragraphs are dropped.
    """
    en_w, ay_w = len(en.split()), len(ay.split())
    if en_w == 0 or ay_w == 0:
        return False
    return low <= (en_w / ay_w) <= high

def sequence_length_ok(en: str, ay: str,
                       tokenizer, max_tokens: int = 250) -> bool:
    """
    Reject pairs that exceed the model's max sequence length, which
    matters mainly for folk-story paragraphs.
    """
    return (len(tokenizer.tokenize(en)) <= max_tokens
            and len(tokenizer.tokenize(ay)) <= max_tokens)
```

Dedup: exact-match on `(en_normalized, ay_normalized)`. Additionally, run an embedding-based near-duplicate detection across the full corpus to catch parallel-passage repetition in the gospels and the chronicler vs. kings overlap. Drop near-duplicates that would otherwise cross train/test split lines.

After filtering, the researcher (via the Phase A app) audits a random 100-pair sample for alignment quality. If >10% misaligned, return to alignment work before proceeding.

### 0.5 Held-Out Test Set Construction
- status: todo
- type: task
- id: ayoreo_translation.data.test_set
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.data.filter]
<!-- content -->

Split rules — designed to prevent leakage given the corpora's structural repetition:

- **Bible**: hold out whole books, not verses. Test books: `Ruth`, `Jonah`, `Philemon`, `2_John`, `3_John` (small, varied, span both testaments). Validation books: `Esther`, `Habakkuk`, `Titus`. Result roughly 90/5/5 by verse count and far more honest than random verse-level splits.
- **Folk stories**: hold out whole stories. Aim for 20 stories test, 10 stories validation, 100 stories training — roughly 75/8/17 by paragraph count.
- **Dictionary** (if acquired): random pair-level split is fine — dictionary examples are decontextualized so leakage risk is low.

Plus a curated **challenge set** of ~50 hand-picked items: morphologically complex verb forms, culturally specific terminology, idioms, and explicitly out-of-domain sentences (modern conversational, technical, present-tense first/second person). The challenge set is the qualitative gut-check at every iteration.

Save splits as `data/{train,val,test}.jsonl` with `src` preserved, plus `data/challenge.jsonl`. Commit the data file hashes for reproducibility.

### 0.6 Alignment Audit of LLM-Aligned Folk Stories
- status: todo
- type: task
- id: ayoreo_translation.data.alignment_audit
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.data.test_set, ayoreo_translation.annotation.tier2]
<!-- content -->

The 114 folk stories with LLM-produced `alignment_map` have not been spot-checked. Paragraph-level alignment is fuzzier than verse-level because translators reorganize narrative content — fusing paragraphs, splitting them, adding cultural framing.

Audit protocol: random sample of 30–50 paragraph pairs, displayed side-by-side via the Phase A app's alignment-audit mode. The researcher tags each as `aligned`, `partial`, or `misaligned`. Decision:

- <10% misaligned → proceed; alignment quality is acceptable
- 10–20% misaligned → flag affected stories with `alignment: suspect`, downweight in training
- \>20% misaligned → re-run LLM alignment with a better prompt or back off to looser sentence-level alignment within paragraph pairs

This task is blocked by Phase A.3 (tier-2 app build) because the audit happens through the app.

## Phase A — Annotation Tool and Active Data Generation
- status: todo
- type: task
- id: ayoreo_translation.annotation
- owner: researcher
- estimate: 1-8w (tier-dependent)
- priority: high
- blocked_by: [ayoreo_translation.data.parallel_corpus]
<!-- content -->

A parallel track that builds on whatever fraction of the researcher's time is available, from 1 hour per week to full-time. The architecture is designed so the v1 tool is useful with minimal commitment and each subsequent tier adds capabilities without reworking earlier ones. The recommendation is to **build incrementally**: ship Tier 1, observe what the researcher actually does with it, then expand.

All tiers share the same backbone (A.1). Each tier adds one or more modes to the same Gradio app and the same append-only JSONL data store, so contributions from any tier flow into training with no schema mismatch.

### A.1 Shared Infrastructure
- status: todo
- type: task
- id: ayoreo_translation.annotation.infrastructure
- owner: researcher
- estimate: 3d
<!-- content -->

Built once, used by every tier. The cost is fixed regardless of which tiers we ship.

**Stack**: Gradio for the UI, SQLite or JSONL for storage, Python-only. Single-file deployable. The current LoRA adapter (or RAG baseline pre-training) is loaded into the app so the researcher always sees what the model would produce.

**Data schema** — every contribution is one row, regardless of mode:

```python
# annotation_log.jsonl — one row per researcher action
{
    "id": "ann-2026-05-12-0042",
    "timestamp": "2026-05-12T14:23:11Z",
    "researcher_id": "raul",            # provenance
    "mode": "correct",                   # which tier-mode produced this row
    "src_lang": "en",                    # or "es" if Spanish pivot used
    "src_text": "...",
    "model_version": "lora-v1-step2400", # what the researcher was correcting
    "model_output": "...",               # what the model said (may be null in pure-translation mode)
    "researcher_output": "...",          # the canonical answer
    "register_tag": "narrative",         # <scripture>|<narrative>|<lexical>
    "researcher_confidence": 4,          # 1-5 self-rating
    "naturalness": null,                 # filled in rating mode only
    "adequacy": null,
    "fluency": null,
    "notes": ""
}
```

**Provenance and ethics**: every row stamped with researcher ID and timestamp. Data-use terms agreed in writing before the app goes live — the researcher's contributions are attributable and bounded to project use. Indigenous-language data has a fraught history; getting this right at the start costs nothing.

**Pipeline integration**: a small daemon polls `annotation_log.jsonl` and merges new contributions into `data/researcher_contributions.jsonl`, which is added to the training mix at the next retraining run.

### A.2 Tier 1 — Evaluation Only (minimal: 1–2 hrs/week)
- status: todo
- type: task
- id: ayoreo_translation.annotation.tier1
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.annotation.infrastructure]
<!-- content -->

**What's built**: a single rating screen. The researcher sees an English (or Spanish) source plus one or more candidate Ayoreo translations and rates each on adequacy / fluency / naturalness, plus optional free-text notes.

**Researcher time per session**: ~30 seconds per item. 1 hour/week ≈ 100 ratings/week, 2 hours/week ≈ 200 ratings/week.

**Value to the project**: this alone removes the hardest blocker in the v1 plan — Phase 5.2 evaluation. Without a fluent evaluator, the entire iteration loop is unmeasurable. With even minimal evaluator time, the project becomes navigable. Naturalness as a separate dimension is what makes Bible translationese visible in the metrics.

**Tier-1 app sketch** (~80 lines of Gradio):

```python
# tier1_rating_app.py — minimum viable annotation app
import gradio as gr
import json
from datetime import datetime

def log_rating(item_id, adequacy, fluency, naturalness, notes):
    """
    Append one rating row to annotation_log.jsonl. The row format is the
    same schema used by every later tier — no migration needed when we
    add modes.
    """
    row = {
        "id": f"ann-{datetime.utcnow().isoformat()}-{item_id}",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "mode": "rate",
        "researcher_id": "raul",  # configure per-deployment
        "src_text": current_item["src"],
        "model_output": current_item["candidate"],
        "researcher_output": None,    # rating mode produces no rewrite
        "adequacy": adequacy,
        "fluency": fluency,
        "naturalness": naturalness,
        "notes": notes,
    }
    with open("annotation_log.jsonl", "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return "Saved. Next item below."

# UI: source, candidate, three sliders (1-5), notes box, submit, "next" button
# Items pulled from a priority queue file (see A.7 active learning loop)
```

This tool ships in ~2 days of work. It is useful starting day one.

### A.3 Tier 2 — Add Alignment Audit (light: 3–5 hrs/week)
- status: todo
- type: task
- id: ayoreo_translation.annotation.tier2
- owner: researcher
- estimate: 1d
- blocked_by: [ayoreo_translation.annotation.tier1]
<!-- content -->

**What's added**: a second screen showing a paragraph pair (EN and AYO) side-by-side. The researcher tags it `aligned`, `partial`, or `misaligned`, with an optional corrected alignment.

**Researcher time per session**: ~1 minute per pair. 3 hours/week ≈ 180 audits/week — enough to clear the 114 LLM-aligned story backlog in roughly 1 week.

**Value to the project**: directly unblocks Phase 0.6. Once cleared, switch this mode to ad-hoc use for spot-checking new contributions. If the audit reveals >15% misalignment, this mode supports re-alignment workflows that produce corrected paragraph maps as training data themselves.

**Implementation cost**: ~1 day on top of Tier 1, since it reuses all the infrastructure from A.1.

### A.4 Tier 3 — Add Correction Mode (moderate: 5–10 hrs/week)
- status: todo
- type: task
- id: ayoreo_translation.annotation.tier3
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.annotation.tier2]
<!-- content -->

**What's added**: a correction screen. The app shows the source plus the current model's proposed Ayoreo translation, and the researcher edits the model output into a correct version. This is where the **active learning loop** comes into its own.

**Researcher time per session**: ~2 minutes per correction. 5 hours/week ≈ 150 corrections/week, 10 hours/week ≈ 300 corrections/week. Over 8 weeks at the upper end, that's ~2,400 new high-quality pairs — comparable in size to a substantial new corpus, but targeting the model's specific weak points.

**Value to the project**: each corrected pair is worth several "blind" translations because the example was *chosen* by the active learning system (see A.7) as a high-information case. Over time, corrections compound: the next training run produces better proposals, so the researcher spends less time per item, and pivots toward harder cases.

**Items pulled from**: the priority queue in A.7, biased toward (a) out-of-distribution challenge-set sentences, (b) low-confidence model outputs, (c) sentences from underrepresented domains.

**Implementation cost**: ~2 days. Reuses A.1 infrastructure; adds the priority-queue feeder and a corrections-specific submit path.

### A.5 Tier 4 — Add Bible Naturalness Rewrites (substantial: 10–20 hrs/week)
- status: todo
- type: task
- id: ayoreo_translation.annotation.tier4
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.annotation.tier3]
<!-- content -->

**What's added**: a Bible-rewrite screen. The app shows an English Bible verse alongside the existing AYO translation, and asks "would you say this in natural Ayoreo? If not, rewrite it." The researcher either approves (one click) or rewrites (free-text edit).

**Researcher time per session**: ~3–4 minutes per rewrite (longer than corrections because the comparison is more nuanced — the existing translation is comprehensible, just non-native). 10 hours/week ≈ 150 reviews/week with maybe 70% requiring rewrites; 20 hours/week ≈ 300 reviews/week.

**Value to the project — potentially the highest-leverage activity in the entire plan.** This directly attacks the translationese problem rather than diluting it. After 8 weeks at 20 hrs/week, the researcher could have rewritten ~1,500 Bible verses into natural register. That produces:

- A second AYO side for every rewritten verse → same content, two registers → ideal training data for source-tag conditioning
- A high-quality "natural-Ayoreo" corpus of ~1,500 pairs that becomes the Stage-2 training data alongside folk stories
- An empirical measurement of how often the existing Bible translation is acceptable vs. needs rewriting — a finding worth publishing independent of the model

**Implementation cost**: ~2 days. Same data schema; new screen that loads Bible pairs in order or by sampling strategy.

### A.6 Tier 5 — Add Folk-Story Collection (maximal: 20+ hrs/week)
- status: todo
- type: task
- id: ayoreo_translation.annotation.tier5
- owner: researcher
- estimate: 4d
- blocked_by: [ayoreo_translation.annotation.tier4]
<!-- content -->

**What's added**: an audio-recording-plus-transcription mode for new folk stories collected from elders, and a glossary-curation screen. This is the only tier that involves field work; the others can be done entirely at a desk.

**Workflow**:
1. Researcher (or community contact) records an elder telling a story (Ayoreo audio).
2. Researcher transcribes the audio in-app (or imports a transcription).
3. Researcher translates the Ayoreo transcription into English (and optionally Spanish).
4. The new story flows into `data/folk_stories_v2/` and the training pipeline.

**Researcher time**: highly variable. Field work and transcription is slow — 1 hour of audio might take 4–8 hours to transcribe and translate. At 20+ hrs/week, expect ~2–5 new stories per month, which over 8 weeks could produce 200–600 new native-speaker paragraph pairs.

**Value to the project**: directly grows the most valuable training corpus we have. Every new folk-story pair is worth multiple Bible pairs at this point. Also produces audio material that is independently valuable for the community and for any future speech-related work.

**Glossary curation**: when the researcher encounters a recurring term that needs canonical translation (proper nouns, cultural terms, terminology), they add it to `data/glossary.jsonl`. This feeds Phase 6.2's terminology lookup and substitutes for an external dictionary if one never materializes.

**Implementation cost**: ~4 days because of audio handling and the more complex multi-step workflow. Gradio supports audio components natively, so this stays within the same stack.

### A.7 Active Learning Loop and Retraining Cadence
- status: todo
- type: task
- id: ayoreo_translation.annotation.active_learning
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.annotation.tier3]
<!-- content -->

The mechanism that makes researcher time high-leverage rather than just additive.

**Priority queue**: a ranked list of items the app should show the researcher next. Built from several signals:

```python
def priority_score(item: dict, model, retrieval_index) -> float:
    """
    Score an item by how informative researcher attention to it would be.
    Higher score = show this sooner.
    """
    # Signal 1: model uncertainty — low-confidence outputs are likely wrong
    # and benefit most from correction.
    uncertainty = -model.log_probability(item["candidate"]) / len(item["candidate"])

    # Signal 2: out-of-distribution by retrieval distance — items far from
    # any training example are the ones the model has no signal for.
    nearest_neighbor_dist = retrieval_index.nearest_distance(item["src"])

    # Signal 3: domain coverage — if the current training data is 89% Bible,
    # non-Bible items get a boost.
    domain_bonus = 2.0 if item.get("domain") != "bible" else 1.0

    return (uncertainty + 0.5 * nearest_neighbor_dist) * domain_bonus
```

**Retraining cadence**: every ~500 new high-quality researcher contributions, kick off a fresh LoRA fine-tune. The new model becomes the basis for the next round of corrections, so improvements compound. This is a virtuous loop: better model → easier correction sessions → more pairs per hour → better next model.

**Stopping criterion**: when researcher corrections converge on minor edits rather than substantive rewrites, the model has converged on the available signal. At that point, shift the researcher's time toward Tier 4 (naturalness rewrites) and Tier 5 (new folk stories) — both produce data the model has no other way to acquire.

### A.8 Spanish Pivot Workflow (cross-cuts all tiers)
- status: todo
- type: task
- id: ayoreo_translation.annotation.spanish_pivot
- owner: researcher
- estimate: 1d
<!-- content -->

A trilingual researcher in a South American context likely has stronger Spanish↔Ayoreo intuitions than English↔Ayoreo intuitions. Every annotation mode should expose Spanish as an alternative source language.

Implementation: when an item is loaded, the app auto-generates a Spanish version of the English source via NLLB (cached on first generation). The researcher can toggle which source language they prefer for any given item. Both source languages are stored in the contribution row, producing (EN, ES, AYO) triples whenever both are provided. These triples are training-gold for NLLB's many-to-many architecture and may make Spanish→Ayoreo the better-performing inference direction overall.

**Cost**: ~1 day to wire in. NLLB inference is fast enough to do this on-demand without preprocessing.

## Phase 1 — Baseline Without Training
- status: todo
- type: task
- id: ayoreo_translation.baseline
- owner: researcher
- estimate: 1w
- blocked_by: [ayoreo_translation.data.test_set]
<!-- content -->

Establish a non-training baseline before investing in fine-tuning. Three deliverables: a number to beat, the evaluation harness used by every subsequent phase, and an early sanity check on retrieval-augmented prompting.

### 1.1 Retrieval Index for Few-Shot Prompting
- status: todo
- type: task
- id: ayoreo_translation.baseline.retrieval
- owner: researcher
- estimate: 2d
<!-- content -->

Index the training set with LaBSE embeddings for cross-lingual sentence similarity. Build separate retrieval indices for each source corpus (Bible, folk_story, dictionary if available) so we can control retrieval-mix per query.

```python
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss

encoder = SentenceTransformer("sentence-transformers/LaBSE")
en_embeddings = encoder.encode([p["en"] for p in train_pairs],
                               normalize_embeddings=True)
index = faiss.IndexFlatIP(en_embeddings.shape[1])
index.add(en_embeddings.astype(np.float32))
```

### 1.2 LLM Baseline with RAG
- status: todo
- type: task
- id: ayoreo_translation.baseline.rag_llm
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.baseline.retrieval]
<!-- content -->

Few-shot prompting against Claude or GPT-4-class models. Retrieve k=8 nearest training pairs, format as in-context examples. Evaluate on the validation set; record per-domain breakdowns. This is the floor — if LoRA cannot beat it, LoRA is not the right tool for this corpus.

### 1.3 Evaluation Harness
- status: todo
- type: task
- id: ayoreo_translation.baseline.eval_harness
- owner: researcher
- estimate: 3d
<!-- content -->

Built once, used everywhere. Each evaluation run produces a single JSON record with all metrics, model identifier, and data split — making phases directly comparable.

Metrics:

- **chrF / chrF++** — primary. Character-level F-score is more reliable than BLEU for morphologically complex low-resource languages.
- **BLEU** — secondary; included for comparability with published low-resource MT.
- **TER** — diagnostic; shows where outputs are *close but wrong*.
- **Embedding similarity** — LaBSE cosine between hypothesis and reference. Catches semantic adequacy when surface metrics underrate paraphrase.
- **Per-domain breakdowns** — same metrics computed separately for Bible-test, folk-story-test, and challenge set. The gap between these is the most informative diagnostic in the project.

```python
import sacrebleu

def evaluate(hypotheses, references, src_tags=None):
    """
    Compute chrF, BLEU, TER. If src_tags provided, also produce
    per-source breakdowns. Returns a flat dict suitable for run logging.
    """
    result = {
        "chrf": sacrebleu.corpus_chrf(hypotheses, [references]).score,
        "bleu": sacrebleu.corpus_bleu(hypotheses, [references]).score,
        "ter":  sacrebleu.corpus_ter(hypotheses, [references]).score,
        "n":    len(hypotheses),
    }
    if src_tags:
        for src in set(src_tags):
            idx = [i for i, t in enumerate(src_tags) if t == src]
            sub_h = [hypotheses[i] for i in idx]
            sub_r = [references[i] for i in idx]
            result[f"chrf_{src}"] = sacrebleu.corpus_chrf(sub_h, [sub_r]).score
    return result
```

## Phase 2 — Tokenizer Preparation
- status: todo
- type: task
- id: ayoreo_translation.tokenizer
- owner: researcher
- estimate: 4d
- blocked_by: [ayoreo_translation.data.test_set]
<!-- content -->

The unsexy variable that quietly determines training efficiency. NLLB's tokenizer is decent for many low-resource languages but unverified for Ayoreo specifically.

### 2.1 Tokenization Analysis
- status: todo
- type: task
- id: ayoreo_translation.tokenizer.analysis
- owner: researcher
- estimate: 1d
<!-- content -->

Measure baseline fragmentation. Compare chars-per-token on Ayoreo vs English vs Spanish using NLLB's tokenizer:

```python
def chars_per_token(sentences, tokenizer):
    """Average chars/token across a corpus. Higher = less fragmentation."""
    ratios = [len(s) / max(len(tokenizer.tokenize(s)), 1) for s in sentences]
    return sum(ratios) / len(ratios)

# Healthy: ~3-5 chars/token for English. <60% of English ratio for AY signals
# severe fragmentation and triggers tokenizer extension (2.2).
```

### 2.2 Tokenizer Extension
- status: todo
- type: task
- id: ayoreo_translation.tokenizer.extend
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.tokenizer.analysis]
<!-- content -->

Only if 2.1 shows severe fragmentation. Train a small SentencePiece on monolingual Ayoreo (Phase 3's corpus), add top-frequency subwords as new tokens — conservatively, 500–2,000 new tokens. Resize model embeddings; the new rows must be learned in Phase 4.

## Phase 3 — Continued Pre-training on Monolingual Ayoreo
- status: todo
- type: task
- id: ayoreo_translation.pretrain
- owner: researcher
- estimate: 1w
- blocked_by: [ayoreo_translation.tokenizer]
- priority: medium
<!-- content -->

Un-deprioritized in v2 given the AYO-side token imbalance. Even modest continued-pretraining on native-speaker monolingual text helps the model absorb Ayoreo morphology before being asked to learn alignment.

### 3.1 Monolingual Corpus Curation
- status: todo
- type: task
- id: ayoreo_translation.pretrain.corpus
- owner: researcher
- estimate: 2d
<!-- content -->

Pool: the 2 AYO-only folk stories from Phase 0.2, plus any other monolingual Ayoreo we can scrape or collect (community publications, transcribed elder interviews, Tier-5 folk-story collection output). Normalize with the same NFC pipeline. Save as `data/monolingual_ay.txt`, one sentence per line.

Even a few thousand tokens of native-speaker monolingual text is leverage given the AYO-side imbalance. If the researcher is producing folk-story transcriptions via Tier 5, their AYO sides flow here as well.

### 3.2 Masked-LM Pretraining Pass
- status: todo
- type: task
- id: ayoreo_translation.pretrain.run
- owner: researcher
- estimate: 4d
- blocked_by: [ayoreo_translation.pretrain.corpus]
<!-- content -->

Short denoising-objective pass on monolingual Ayoreo: span masking on the encoder side, LR ~1e-5, 1–3 epochs over the corpus with aggressive early stopping on a held-out monolingual perplexity slice. Hold out a small competency probe (Spanish↔English samples) and check it before/after to detect catastrophic forgetting of multilingual representations.

Stop criterion: if continued pretraining doesn't improve validation chrF in Phase 4, it was either unnecessary or harmful. Don't repeat without diagnosing why.

## Phase 4 — Two-Stage LoRA Fine-Tuning
- status: todo
- type: task
- id: ayoreo_translation.lora
- owner: researcher
- estimate: 2w
- blocked_by: [ayoreo_translation.baseline.eval_harness, ayoreo_translation.tokenizer]
<!-- content -->

The core training phase. Restructured in v2 into two sequential stages because the 89% AYO scripture imbalance cannot be cured by sampling alone — we need an isolated phase where loss is computed only on native-speaker Ayoreo.

### 4.1 Base Model Selection
- status: todo
- type: task
- id: ayoreo_translation.lora.base_model
- owner: researcher
- estimate: 1d
<!-- content -->

Small calibration run (~500 examples, identical LoRA settings) on three candidates:

- `facebook/nllb-200-distilled-600M` — default; fast iteration
- `facebook/nllb-200-1.3B` — bigger; possibly better on hard sentences
- `facebook/mbart-large-50-many-to-many-mmt` — backup if NLLB underperforms

Pick winner on validation chrF. Record in `experiments/base_model_selection.json`.

### 4.2 LoRA Configuration with Source Tags
- status: todo
- type: task
- id: ayoreo_translation.lora.config
- owner: researcher
- estimate: 1d
- blocked_by: [ayoreo_translation.lora.base_model]
<!-- content -->

Two changes from v1: larger starting rank, MLP projections in `target_modules` from the start. Plus source-tag prefixes on every training example.

```python
from peft import LoraConfig, TaskType

# v2: bumped from r=8 to r=16; added gate_proj/up_proj from the start.
# More data justifies more capacity; the 89% AYO imbalance also means
# the model needs more capacity to learn the minority register.
lora_config = LoraConfig(
    task_type=TaskType.SEQ_2_SEQ_LM,
    r=16,
    lora_alpha=32,
    lora_dropout=0.1,
    bias="none",
    target_modules=[
        "q_proj", "v_proj", "k_proj", "out_proj",  # attention
        "gate_proj", "up_proj",                     # MLP (was held back in v1)
    ],
)
```

Source-tag prefix format:

```python
def format_with_tag(example: dict) -> dict:
    """
    Prefix every training example with a register tag.
    At inference, the tag becomes a controllable knob:
        <narrative>   → conversational/natural register
        <scripture>   → biblical register
        <lexical>     → dictionary-style register (if dictionary acquired)
    """
    tag = {"folk_story": "<narrative>",
           "bible":      "<scripture>",
           "dictionary": "<lexical>"}[example["src"]]
    return {
        "input": f"{tag} {example['en']}",
        "output": example["ay"],
    }
```

### 4.3 Training Mix and Weighting Scheme
- status: todo
- type: task
- id: ayoreo_translation.lora.mix
- owner: researcher
- estimate: 1d
- blocked_by: [ayoreo_translation.lora.config]
<!-- content -->

Explicit per-source sampling weights. Calibrated against the actual AYO token counts to balance gradient signal as much as is feasible without distorting representational learning.

```python
def build_weighted_sampler(dataset):
    """
    Sampling weights designed around the observed corpus imbalance:
    - Bible:      89% of AYO tokens → baseline weight 1.0
    - Folk stories: 11% of AYO tokens → 6x oversampling brings effective
      gradient contribution roughly to parity per epoch.
    - Dictionary (if acquired): typically short, clean → 8x to compensate
      for low per-pair token count.
    - Researcher contributions: high quality, native register → 8x.

    Ablation worth running: undersample bible to 0.5x. The Bible's vocabulary
    and patterns repeat heavily; you don't need 20k pairs to absorb them,
    and undersampling speeds Stage 1 while shifting loss balance favorably.
    """
    weights = []
    for ex in dataset:
        if ex["src"] == "folk_story":
            weights.append(6.0)
        elif ex["src"] == "dictionary":
            weights.append(8.0)
        elif ex["src"] == "researcher":  # Tier 3+ contributions
            weights.append(8.0)
        else:                              # bible
            weights.append(1.0)
    return torch.utils.data.WeightedRandomSampler(
        weights, num_samples=len(dataset), replacement=True
    )
```

### 4.4 Stage 1 — Full-Mix Training
- status: todo
- type: task
- id: ayoreo_translation.lora.stage1
- owner: researcher
- estimate: 1w
- blocked_by: [ayoreo_translation.lora.mix]
<!-- content -->

The big training run. Hugging Face `Seq2SeqTrainer` with:

- Effective batch size 32–64 via gradient accumulation
- LR 3e-4 (LoRA-typical; ~10x higher than full-fine-tuning rates because adapters start near zero)
- Warmup 6% of total steps; cosine decay
- 8–15 epochs target with early stopping on validation chrF, patience=3
- Evaluation every 500 steps
- Label smoothing 0.1
- Best-checkpoint-only on validation chrF (use Bible-test chrF *and* folk-story-test chrF; promote a checkpoint only if both improve — protects against the model overfitting one register)
- Direction handling: interleave EN→AY and AY→EN training examples for joint bidirectional training
- Source tags applied per 4.2

Watch for overfitting around epoch 5–8. Bible vocabulary is constrained enough that the model can memorize it; early stopping must trigger when validation chrF degrades, not when training loss flattens.

### 4.5 Stage 2 — Native-Register Fine-Tune
- status: todo
- type: task
- id: ayoreo_translation.lora.stage2
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.lora.stage1]
<!-- content -->

Load the Stage-1 adapter; continue fine-tuning on a **native-register-only** subset:

- Folk stories (training split)
- Researcher contributions from Phase A (Tier 3+ corrections, Tier 4 naturalness rewrites if available)
- Dictionary examples if available and judged high-quality

Bible pairs are **excluded** from Stage 2 entirely. This is the whole point — give the model an isolated phase where the gradient signal is 100% native-speaker.

Hyperparameters:

- LR 5e-5 (much lower than Stage 1 — we're refining, not relearning)
- 200–500 steps with early stopping on folk-story validation chrF
- Same LoRA rank, same architecture as Stage 1 (continuing the same adapter)

Save both adapters separately as `ayoreo_lora_stage1` and `ayoreo_lora_stage2`. Both go through Phase 5 evaluation; ship whichever produces better naturalness scores without unacceptable adequacy regression.

### 4.6 Checkpoint Selection and Adapter Export
- status: todo
- type: task
- id: ayoreo_translation.lora.export
- owner: researcher
- estimate: 1d
- blocked_by: [ayoreo_translation.lora.stage2]
<!-- content -->

Export Stage-1 and Stage-2 adapters separately. Each gets a `MODEL_CARD.md` documenting base model, LoRA config, training data hash, training metrics on all per-domain breakdowns, and known failure modes.

```python
model.save_pretrained("checkpoints/ayoreo_lora_stage1")
# After Stage 2:
model.save_pretrained("checkpoints/ayoreo_lora_stage2")
```

Both adapters become inputs to the Phase 6 inference pipeline. The deployment can switch between them based on register need (Stage 1 may be preferred for scripture-style inputs).

## Phase 5 — Evaluation and Iteration
- status: todo
- type: task
- id: ayoreo_translation.eval
- owner: researcher
- estimate: 1w
- blocked_by: [ayoreo_translation.lora.export, ayoreo_translation.annotation.tier1]
<!-- content -->

Non-linear by design. Error analysis may send us back to Phase 0 (more data), Phase 2 (tokenizer), Phase 4 (different hyperparameters), or to Tier 4 (more naturalness rewrites). Iterate at most twice before shipping — perfectionism on this data scale is a trap.

### 5.1 Automatic Evaluation
- status: todo
- type: task
- id: ayoreo_translation.eval.automatic
- owner: researcher
- estimate: 1d
<!-- content -->

Run the Phase 1.3 harness on Stage-1 adapter, Stage-2 adapter, RAG baseline, and zero-shot NLLB. Per-domain breakdowns required: Bible-test, folk-story-test, challenge-set.

The diagnostic table that matters:

```
Model            | Bible chrF | Folk chrF | Challenge chrF | Bible↔Folk gap
-----------------|-----------:|----------:|---------------:|---------------:
RAG baseline     |        ?   |       ?   |            ?   |             ?
Zero-shot NLLB   |        ?   |       ?   |            ?   |             ?
LoRA Stage 1     |        ?   |       ?   |            ?   |             ?
LoRA Stage 2     |        ?   |       ?   |            ?   |             ?
```

A large Bible↔Folk gap after Stage 1 justifies Stage 2. A small gap after Stage 2 indicates the model successfully crossed register. A regression in Bible chrF from Stage 1 to Stage 2 is expected and acceptable up to a point — that's the cost of natural register, and is exactly why we keep both adapters.

### 5.2 Human Evaluation
- status: todo
- type: task
- id: ayoreo_translation.eval.human
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.eval.automatic]
<!-- content -->

The researcher rates ~100 test sentences plus the full 50-sentence challenge set via the Phase A app's rating mode. Rubric is **four-dimensional**:

- **Adequacy** (1–5): preserves meaning?
- **Fluency** (1–5): grammatically natural?
- **Terminology** (1–5): cultural/domain terms handled correctly?
- **Naturalness** (1–5): sounds like a native speaker, or like a translation?

Naturalness is the dimension that catches translationese — automatic metrics will look fine on translationese output because it matches the (translationese-biased) reference, but a fluent speaker hears it immediately. Treat naturalness scores as the source of truth and automatic metrics as a fast proxy.

Run human eval on both Stage-1 and Stage-2 adapters side-by-side. Researcher rates blind (model identity hidden).

### 5.3 Error Analysis and Iteration Decision
- status: todo
- type: task
- id: ayoreo_translation.eval.error_analysis
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.eval.human]
<!-- content -->

Categorize errors on a stratified sample of ~50 test outputs:

- **Lexical** — wrong word, grammar OK
- **Morphological** — wrong inflection, wrong agreement
- **Syntactic** — phrase ordering off
- **Hallucination** — content not in source
- **Copy failure** — proper nouns mangled
- **Translationese** — comprehensible but L2-flavored register
- **Domain shift** — works on register A, fails on B

Dominant category determines next move:

- Lexical → strengthen Phase 6.2 terminology lookup; commission glossary work in Tier 5
- Morphological → revisit tokenizer (Phase 2); more Phase 3 pretraining
- Hallucination → reduce LoRA rank or add dropout (Phase 4.2)
- Translationese → more Tier 4 naturalness rewrites; extend Stage 2
- Domain shift → rebalance training mix (Phase 4.3); more Tier 3 corrections in weak domains

Log the decision in `experiments/iteration_log.md`. After at most two full iterations, ship and move to Phase 6.

## Phase 6 — Hybrid Inference Pipeline
- status: todo
- type: task
- id: ayoreo_translation.inference
- owner: researcher
- estimate: 1w
- blocked_by: [ayoreo_translation.eval]
<!-- content -->

The end product. The LoRA adapters are one component in a three-stage pipeline; the hybrid setup outperforms model-alone on extreme-low-resource settings.

### 6.1 LoRA Inference Service
- status: todo
- type: task
- id: ayoreo_translation.inference.lora_service
- owner: researcher
- estimate: 2d
<!-- content -->

Wrap the LoRA-adapted NLLB model as a service exposing `translate(text, src_lang, tgt_lang, register_tag=None) -> str`. The `register_tag` argument selects the source-tag prefix learned in Phase 4.2, exposing the register knob to API callers.

Beam search with `num_beams=5`, `length_penalty=1.0` defaults. For deployment, `model.merge_and_unload()` collapses the LoRA path into the base model — zero runtime overhead.

Both Stage-1 and Stage-2 adapters are deployable; expose adapter selection at request time so callers can choose biblical vs. natural register depending on use case.

### 6.2 Refinement Layer with Optional Glossary
- status: todo
- type: task
- id: ayoreo_translation.inference.refiner
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.inference.lora_service]
<!-- content -->

Composition: LoRA proposes → RAG retrieves similar pairs → strong general LLM (Claude / GPT-4) refines for fluency and terminology, **constrained to stay close to the LoRA proposal**.

The Spanish pivot may show up here too: if Spanish→Ayoreo turned out to be the stronger inference direction in Phase 5, the pipeline can route English requests through Spanish first, then refine.

**If a dictionary is acquired** at any point, integrate here as a terminology lookup: for any proper noun, cultural term, or domain term in the source, inject its canonical Ayoreo form into the refiner's prompt. This is the single highest-ROI inference-time intervention. The Phase A glossary curation (Tier 5) feeds this same lookup if it grows organically through researcher work, providing a substitute path if no external dictionary materializes.

### 6.3 Confidence Scoring and Fallback
- status: todo
- type: task
- id: ayoreo_translation.inference.confidence
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.inference.refiner]
<!-- content -->

Surface confidence per output:

- Length-normalized sequence log-likelihood from the LoRA model
- Agreement score between LoRA proposal and refiner output (large rewrites = LoRA was struggling)
- Retrieval similarity of source to nearest training neighbor (low = OOD)

Below threshold → return with a flag asking for human review rather than presenting as authoritative. The cost of a confidently-wrong translation in a 4,500-speaker language is high; calibrated humility matters.

## Phase 7 — Knowledge Capture
- status: todo
- type: task
- id: ayoreo_translation.kb_capture
- owner: researcher
- estimate: 5d
- blocked_by: [ayoreo_translation.inference]
<!-- content -->

Per convention rule 11. Five artifacts to produce, expanded from v1 to reflect the new annotation track:

- **New `how-to`** — `LOW_RESOURCE_TRANSLATION_LORA_SKILL.md`: generalized procedure for two-stage LoRA fine-tuning on imbalanced low-resource language pairs. `scope: general`. Scaffold during Phase 4; populate as 4–6 complete.
- **New `reference`** — `AYOREO_ORTHOGRAPHY_REF.md`: canonical orthographic-normalization decisions from Phase 0.3, with rationale. `scope: project-specific`.
- **New `explanation`** — `AYOREO_TOKENIZER_EXPLANATION.md`: why tokenizer fragmentation matters for low-resource MT, with Phase 2 measurements as data. `scope: general`.
- **New `how-to`** — `ACTIVE_LEARNING_ANNOTATION_TOOL_SKILL.md`: tiered Gradio annotation app design with priority-queue active learning. `scope: general`. Highly reusable for other low-resource language projects.
- **New `explanation`** — `BIBLE_TRANSLATIONESE_DIAGNOSIS_EXPLANATION.md`: methodology and findings around detecting translationese in indigenous-language Bibles via EN:AYO token-ratio analysis. `scope: general`. Independently publishable result.

No existing KB document covers this territory; all five are new.

## Risk Register
- status: todo
- type: task
- id: ayoreo_translation.risks
- owner: researcher
- estimate: 0d
<!-- content -->

Standing risks, reviewed at every phase boundary.

- **Stage 2 may not recover natural register** — the model may have memorized Bible patterns too deeply for 500 steps of folk-story-only training to dislodge. Mitigation: keep Stage-1 adapter as fallback; if Stage 2 underperforms on naturalness, extend it (more researcher contributions, longer training) before declaring failure.
- **Researcher commitment unknown** — entire Phase A is contingent on at-least-minimal researcher availability. Mitigation: Tier 1 is useful in 1 hour/week; build that first and scale only if commitment grows.
- **Folk-story alignment quality** — 114 LLM-aligned stories not yet audited (Phase 0.6 addresses). If alignment is poor, training will be capped.
- **Catastrophic forgetting from Phase 3** — continued pretraining may degrade multilingual competence. Mitigation: hold-out competency probes before/after pretraining.
- **Community/ethical concerns** — Indigenous-language translation systems have a fraught history. Mitigation: secure explicit community consent for data use and deployment before Phase 6 ships; Phase A's data-use terms documented at app launch.
- **Spanish-pivot disappoints** — researcher's Spanish intuitions may not actually be stronger than English, or NLLB's Spanish→Ayoreo path may not outperform English→Ayoreo. Mitigation: measure empirically in Phase 5; the workflow is optional.

## Open Questions
- status: todo
- type: task
- id: ayoreo_translation.open_questions
- owner: researcher
- estimate: 0d
<!-- content -->

To resolve during Phase 0 / Phase A.1 startup:

- **Researcher's hours per week** — determines which Phase A tier to build first. Lower bound: ship Tier 1 immediately.
- **Dictionary availability** — if acquired, slot into Phase 4.3 mix and Phase 6.2 lookup with no plan restructuring. If not, glossary growth happens through Tier 5 work or is omitted.
- **Bolivian vs Paraguayan Ayoreo variety** — affects whether to tag dialect at training time. Bible likely fixes one variety; folk stories may mix. Worth asking the researcher early.
- **Translator history of the Bible** — did the translator work with native consultants? Was the translation reviewed and revised? Affects how strong the translationese signal is expected to be, and whether some Bible books are more naturalness-friendly than others.
- **Community consent boundaries** — what content can the deployed system translate? Any topics off-limits? Resolve before Phase 6.
- **Folk-story narrator diversity** — 130 stories from few or many narrators? Affects how much linguistic variety the model actually sees.
