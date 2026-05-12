# Ayoreo–English Translation Pipeline (LoRA + Hybrid Inference)
- status: in-progress
- type: plan
- id: ayoreo_translation
- description: End-to-end plan for building an English↔Ayoreo machine translation system on extremely limited parallel data, using NLLB-200 as the base, parameter-efficient LoRA fine-tuning, optional continued pre-training on monolingual Ayoreo, and a hybrid RAG-refinement inference layer.
- label: [planning, backend]
- injection: informational
- volatility: evolving
- owner: researcher
- estimate: 8w
- priority: high
- last_checked: 2026-05-12
<!-- content -->

This plan covers the construction of a bidirectional translation system between English and **Ayoreo** (Zamucoan family; spoken by ~4,500 people across Bolivia and Paraguay). Ayoreo is functionally absent from mainstream LLM pretraining corpora, so the core technical risk is **representation cold-start**: the base model has no prior structure to nudge. The plan is staged so each phase produces a usable artifact and a measurable improvement over the previous one — we never depend on a single big training run succeeding.

Three design decisions frame everything below:

1. **NLLB-200 as the base model** rather than a general LLM. NLLB was purpose-built for low-resource translation across 200 languages, including several South American indigenous languages. Its multilingual subword tokenizer fragments Ayoreo far less aggressively than English-dominant tokenizers, and its encoder-decoder architecture is the right shape for the task.
2. **LoRA over full fine-tuning**, with deliberately small rank. With likely <5,000 parallel pairs, full fine-tuning would overfit and induce catastrophic forgetting of the base model's multilingual competence. LoRA's tiny parameter count is a regularizer here — a feature, not just an efficiency win.
3. **Hybrid inference, not pure model output**. The LoRA-tuned model proposes a translation; a refinement layer (RAG over the parallel corpus + a strong general LLM) corrects fluency and terminology. This compensates for the unavoidable hallucinations that come with training on a tiny corpus.

The plan assumes a single researcher working part-time over ~8 weeks. It will be revisited at the end of Phase 1 once we have a baseline number to anchor expectations against.

## Phase 0 — Data Foundation
- status: in-progress
- type: task
- id: ayoreo_translation.data
- owner: researcher
- estimate: 2w
<!-- content -->

Everything downstream is bounded by the quality of this phase. The single biggest determinant of final translation quality on low-resource tasks is alignment accuracy in the parallel corpus — misaligned pairs teach the model to hallucinate confidently. We optimize for **clean and labeled** over **large**.

### 0.1 Source Inventory and Cataloging
- status: in-progress
- type: task
- id: ayoreo_translation.data.inventory
- owner: researcher
- estimate: 3d
<!-- content -->

Catalog every Ayoreo source we have access to, with provenance, license/permission status, register, and rough size. Suspected sources include: ayore.org scraped material, Bible portions, dictionary entries with example sentences, oral-history transcripts, and any community-produced educational material.

For each source, record in `data/sources.csv`:

- `source_id` — short identifier
- `source_type` — one of `religious`, `dictionary`, `oral_transcript`, `news`, `educational`, `other`
- `orthography` — which spelling convention is used (sources often diverge)
- `parallel_available` — whether English/Spanish aligned text exists
- `est_sentences` — rough sentence count
- `permission_status` — community / publisher permission for use, where required
- `notes` — anything else worth remembering six months from now

This catalog drives later domain balancing and per-source error analysis.

### 0.2 Parallel Corpus Construction
- status: in-progress
- type: task
- id: ayoreo_translation.data.parallel_corpus
- owner: researcher
- estimate: 5d
- blocked_by: [ayoreo_translation.data.inventory]
<!-- content -->

Produce `data/parallel.jsonl` — one JSON object per aligned pair. Target format:

```python
# data/parallel.jsonl — UTF-8, NFC-normalized, one object per line
{"id": "bible-mat-5-3",  "src": "religious",     "en": "...",  "ay": "..."}
{"id": "dict-0142",      "src": "dictionary",    "en": "...",  "ay": "..."}
{"id": "oral-elders-07", "src": "oral_transcript","en": "...", "ay": "..."}
```

Notes on aligning:

- **Bible portions** are usually verse-aligned and the easiest win. Beware of cases where translators paraphrased rather than translated literally — those pairs are still useful but flag them with `paraphrase: true`.
- **Dictionary example sentences** are extremely high signal per pair — they're typically pedagogical and grammatically clean. Prioritize these.
- **Oral transcripts** are the hardest to align; consider sentence-level alignment tools (e.g., `vecalign`, `LASER` embeddings) but expect to hand-check a sample.

### 0.3 Orthographic Normalization
- status: todo
- type: task
- id: ayoreo_translation.data.normalize
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.data.parallel_corpus]
<!-- content -->

Pick one orthographic convention as canonical and normalize all sources to it. Ayoreo spelling varies across sources (tilde placement, vowel length marking, glottal stop representation). Heterogeneous orthography is functionally equivalent to having less data because the tokenizer sees variants as unrelated tokens.

```python
import unicodedata

def normalize_ayoreo(text: str) -> str:
    """
    Canonical normalization for Ayoreo text.

    Steps:
    1. NFC composition — combines base characters with their diacritics.
       Without this, 'ñ' may exist as either U+00F1 (single char) or
       'n' + U+0303 (combining tilde), and the tokenizer treats them
       as different tokens. NFC fixes this silently.
    2. Strip outer whitespace but preserve internal whitespace structure.
    3. (Optional) Map any source-specific orthographic variants to the
       canonical form. Document each mapping in data/orthography_rules.md.
    """
    text = unicodedata.normalize("NFC", text)
    return text.strip()
```

Maintain `data/orthography_rules.md` (separate `reference` document) listing every variant-to-canonical mapping decision, with rationale. This is the kind of document that future-us will thank present-us for.

### 0.4 Quality Filtering and Deduplication
- status: todo
- type: task
- id: ayoreo_translation.data.filter
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.data.normalize]
<!-- content -->

Apply mechanical filters, then a manual sample review. Mechanical filters:

```python
def length_ratio_ok(en: str, ay: str,
                    low: float = 0.3, high: float = 3.0) -> bool:
    """
    Reject pairs with suspicious word-count ratios.
    Most outliers are misalignments (sentence vs. paragraph).
    Tune (low, high) by inspecting the histogram on a sample first.
    """
    en_words, ay_words = len(en.split()), len(ay.split())
    if en_words == 0 or ay_words == 0:
        return False
    return low <= (en_words / ay_words) <= high

def is_duplicate(pair: dict, seen: set) -> bool:
    """Exact dedup on the (en, ay) tuple after normalization."""
    key = (pair["en"].lower().strip(), pair["ay"].lower().strip())
    if key in seen:
        return True
    seen.add(key)
    return False
```

After filtering, **hand-review a random 5% sample** for alignment quality. If >10% of the sample is misaligned, the corpus is not ready — return to Phase 0.2 with diagnostic notes.

### 0.5 Held-Out Test Set Construction
- status: todo
- type: task
- id: ayoreo_translation.data.test_set
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.data.filter]
<!-- content -->

**Construct the test set before any modeling decisions are made.** Once it exists, do not look at it. Standard splits:

- Training: 80%
- Validation: 10% (for hyperparameter selection, early stopping)
- Test: 10% (touched only at final evaluation, ever)

Stratification rules:

- Stratify by `source` field so each split has the same domain mix.
- Ensure no near-duplicate sentence leaks across splits (use embedding-based duplicate detection, not just exact match).
- Reserve a **small "challenge set"** of ~50 hand-picked sentences: morphologically complex verbs, culturally specific terms, idioms. This is the qualitative gut-check during iteration.

Save splits as `data/{train,val,test}.jsonl` and `data/challenge.jsonl`. Commit hashes for reproducibility.

## Phase 1 — Baseline Without Training
- status: todo
- type: task
- id: ayoreo_translation.baseline
- owner: researcher
- estimate: 1w
- blocked_by: [ayoreo_translation.data.test_set]
<!-- content -->

Establish a non-training baseline before investing in fine-tuning. This phase produces three things: a number to beat, an evaluation harness, and an early sanity check on whether the parallel corpus has enough signal for retrieval-augmented prompting to work at all.

### 1.1 Retrieval Index for Few-Shot Prompting
- status: todo
- type: task
- id: ayoreo_translation.baseline.retrieval
- owner: researcher
- estimate: 2d
<!-- content -->

Index the training set with multilingual sentence embeddings (`paraphrase-multilingual-MiniLM-L12-v2` or `LaBSE`) so we can retrieve the *k* nearest English sentences to a query and use their Ayoreo translations as in-context examples.

```python
from sentence_transformers import SentenceTransformer
import numpy as np
import faiss  # vector index

# LaBSE is trained for cross-lingual sentence similarity — better signal
# than vanilla multilingual MPNet for translation-style retrieval.
encoder = SentenceTransformer("sentence-transformers/LaBSE")

# Build the index over English sides of the training set so we can
# retrieve translation examples given an English query at inference time.
train_pairs = [...]  # loaded from data/train.jsonl
en_embeddings = encoder.encode([p["en"] for p in train_pairs],
                               normalize_embeddings=True)
index = faiss.IndexFlatIP(en_embeddings.shape[1])  # inner product = cosine on normalized vectors
index.add(en_embeddings.astype(np.float32))

def retrieve_examples(query_en: str, k: int = 8) -> list[dict]:
    """Retrieve the k most similar training pairs for a query."""
    q = encoder.encode([query_en], normalize_embeddings=True).astype(np.float32)
    _, idxs = index.search(q, k)
    return [train_pairs[i] for i in idxs[0]]
```

### 1.2 LLM Baseline with RAG
- status: todo
- type: task
- id: ayoreo_translation.baseline.rag_llm
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.baseline.retrieval]
<!-- content -->

Wire up few-shot prompting against Claude or GPT-4-class models. Prompt template (English → Ayoreo direction shown; mirror for the reverse):

```python
def build_prompt(query_en: str, examples: list[dict]) -> str:
    """
    Construct a few-shot translation prompt.
    The model sees retrieved (en, ay) pairs as examples, then is asked
    to translate the query. Keep examples in retrieved order — closest first.
    """
    example_block = "\n\n".join(
        f"English: {ex['en']}\nAyoreo: {ex['ay']}"
        for ex in examples
    )
    return (
        "You are a translation assistant for the Ayoreo language. "
        "Use the example translations below to produce a faithful Ayoreo "
        "translation of the final English sentence. Match the orthographic "
        "conventions shown in the examples.\n\n"
        f"{example_block}\n\n"
        f"English: {query_en}\n"
        "Ayoreo:"
    )
```

Evaluate on the validation set. Record per-domain breakdowns. This baseline is the floor — if LoRA cannot beat it, LoRA is not the right tool for this data scale.

### 1.3 Evaluation Harness
- status: todo
- type: task
- id: ayoreo_translation.baseline.eval_harness
- owner: researcher
- estimate: 3d
<!-- content -->

Build the evaluation harness once and use it for every subsequent phase. It produces a single JSON record per evaluation run capturing all metrics, the model/checkpoint identifier, and the data split used. This makes phases comparable post-hoc.

Metrics:

- **chrF / chrF++** — character-level F-score. Much more reliable than BLEU for low-resource and morphologically complex languages. **This is the primary automatic metric.**
- **BLEU** — included for comparability with other low-resource MT papers; secondary.
- **TER** — translation edit rate; useful for diagnosing where the model is *close but wrong*.
- **Embedding similarity** — cosine similarity between LaBSE embeddings of hypothesis and reference. Loosely captures semantic adequacy when surface-level metrics underrate paraphrase.

Plus a **human rubric** (filled in during Phase 5):

- Adequacy (1–5): does the translation preserve meaning?
- Fluency (1–5): does it read naturally?
- Terminology (1–5): are domain/cultural terms handled correctly?

```python
import sacrebleu

def evaluate(hypotheses: list[str], references: list[str]) -> dict:
    """
    Compute chrF (primary), BLEU, and TER on a parallel hyp/ref pair.
    Returns a flat dict suitable for JSON serialization and run logging.
    """
    return {
        "chrf":  sacrebleu.corpus_chrf(hypotheses, [references]).score,
        "bleu":  sacrebleu.corpus_bleu(hypotheses, [references]).score,
        "ter":   sacrebleu.corpus_ter(hypotheses, [references]).score,
        "n":     len(hypotheses),
    }
```

## Phase 2 — Tokenizer Preparation
- status: todo
- type: task
- id: ayoreo_translation.tokenizer
- owner: researcher
- estimate: 4d
- blocked_by: [ayoreo_translation.data.test_set]
<!-- content -->

The tokenizer is the silent-killer variable for low-resource fine-tuning. If common Ayoreo morphemes shatter into 8–10 byte-level tokens, gradient signal during training is diluted and inference is slower. This phase diagnoses the problem and fixes it if needed.

### 2.1 Tokenization Analysis
- status: todo
- type: task
- id: ayoreo_translation.tokenizer.analysis
- owner: researcher
- estimate: 1d
<!-- content -->

Measure baseline fragmentation on the NLLB-200 tokenizer:

```python
from transformers import AutoTokenizer
import statistics

tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")

# Compare characters-per-token on Ayoreo vs English.
# A healthy ratio is ~3-5 chars/token for English. Anything <2 for Ayoreo
# means severe over-fragmentation and we should consider extending the tokenizer.
ay_sentences = [p["ay"] for p in load_jsonl("data/train.jsonl")]
en_sentences = [p["en"] for p in load_jsonl("data/train.jsonl")]

def chars_per_token(sentences: list[str]) -> float:
    """Average ratio of characters to tokens across a list of sentences."""
    ratios = []
    for s in sentences:
        n_tokens = len(tokenizer.tokenize(s))
        if n_tokens > 0:
            ratios.append(len(s) / n_tokens)
    return statistics.mean(ratios)

print(f"Ayoreo : {chars_per_token(ay_sentences):.2f} chars/token")
print(f"English: {chars_per_token(en_sentences):.2f} chars/token")
```

**Decision rule:** if Ayoreo chars/token is less than 60% of English chars/token, proceed to 2.2. Otherwise skip — NLLB's tokenizer is good enough as-is.

### 2.2 Tokenizer Extension
- status: todo
- type: task
- id: ayoreo_translation.tokenizer.extend
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.tokenizer.analysis]
<!-- content -->

Train a small SentencePiece model on monolingual Ayoreo, then add the top frequent subwords as new tokens to the NLLB tokenizer. Important: every new token added means a new row in the model's embedding matrix that starts from random and must be learned — so add conservatively. Aim for 500–2,000 new tokens, not 10,000.

```python
# After training a SentencePiece model on Ayoreo monolingual text:
new_tokens = load_top_sentencepiece_pieces("ay_spm.model", top_n=1000)

# Add only tokens that aren't already in the vocab — duplicates do nothing
# but bloat the embedding matrix.
truly_new = [t for t in new_tokens if t not in tokenizer.get_vocab()]
n_added = tokenizer.add_tokens(truly_new)

# Critical: resize embeddings so the model has rows for the new tokens.
# These rows start from random init — fine-tuning has to learn them.
model.resize_token_embeddings(len(tokenizer))
```

Re-run 2.1's measurement after extension to confirm fragmentation dropped.

## Phase 3 — Optional Continued Pre-training
- status: todo
- type: task
- id: ayoreo_translation.pretrain
- owner: researcher
- estimate: 1w
- blocked_by: [ayoreo_translation.tokenizer]
- priority: medium
<!-- content -->

Optional but high-leverage. If we have substantial monolingual Ayoreo text (say, >100k tokens) that wasn't used to build parallel pairs, a brief continued-pretraining pass on it teaches the model Ayoreo morphology *before* we ask it to learn alignment. Translation fine-tuning then has a much easier job.

### 3.1 Monolingual Corpus Curation
- status: todo
- type: task
- id: ayoreo_translation.pretrain.corpus
- owner: researcher
- estimate: 2d
<!-- content -->

Gather all Ayoreo text we have not yet used for parallel pairs. Apply the same orthographic normalization from Phase 0.3. Deduplicate. Save as `data/monolingual_ay.txt`, one sentence per line.

### 3.2 Masked-LM Pretraining Pass
- status: todo
- type: task
- id: ayoreo_translation.pretrain.run
- owner: researcher
- estimate: 4d
- blocked_by: [ayoreo_translation.pretrain.corpus]
<!-- content -->

Run a short denoising-objective pass on the monolingual data using NLLB's existing pretraining objective (span masking on the encoder side). One pass over the corpus is usually enough; more invites catastrophic forgetting of the multilingual representations we want to preserve.

Hyperparameters: small learning rate (~1e-5), tiny number of steps (~1–3 epochs over the monolingual data), aggressive early stopping if validation perplexity on a held-out monolingual slice stops improving.

**Stop criterion:** if continued pre-training does not improve validation chrF on the held-out parallel set after Phase 4 fine-tuning, the pre-training step was either unnecessary or actively harmful. Diagnose before retrying.

## Phase 4 — LoRA Fine-Tuning
- status: todo
- type: task
- id: ayoreo_translation.lora
- owner: researcher
- estimate: 2w
- blocked_by: [ayoreo_translation.baseline.eval_harness, ayoreo_translation.tokenizer]
<!-- content -->

The core training phase. Two directions of fine-tuning happen in one run: English→Ayoreo and Ayoreo→English. Training both doubles data utilization and tends to improve representation quality.

### 4.1 Base Model Selection
- status: todo
- type: task
- id: ayoreo_translation.lora.base_model
- owner: researcher
- estimate: 1d
<!-- content -->

Run a small (~500-example) calibration of all three candidates with identical LoRA settings and pick the winner on validation chrF:

- `facebook/nllb-200-distilled-600M` — default choice, small enough for fast iteration
- `facebook/nllb-200-1.3B` — bigger, slower, possibly better on harder sentences
- `facebook/mbart-large-50-many-to-many-mmt` — alternative if NLLB underperforms on this specific language family

Record the calibration in `experiments/base_model_selection.json` for future reference.

### 4.2 LoRA Configuration
- status: todo
- type: task
- id: ayoreo_translation.lora.config
- owner: researcher
- estimate: 1d
- blocked_by: [ayoreo_translation.lora.base_model]
<!-- content -->

Starting point — deliberately conservative for low-data regime:

```python
from peft import LoraConfig, TaskType, get_peft_model

lora_config = LoraConfig(
    task_type=TaskType.SEQ_2_SEQ_LM,  # NLLB is encoder-decoder
    r=8,                              # small rank — regularizer for tiny data
    lora_alpha=16,                    # standard alpha = 2 * r
    lora_dropout=0.1,                 # slightly higher dropout for small datasets
    bias="none",                      # don't train biases — adds params without much gain
    target_modules=[
        "q_proj", "v_proj",           # attention query and value (standard)
        "k_proj", "out_proj",         # adding these gives more capacity
        # MLP layers deliberately omitted at first — add only if r=8 underfits
    ],
)

model = get_peft_model(base_model, lora_config)
model.print_trainable_parameters()
# Expect: ~0.1% trainable, around 4-8M params for the 600M base
```

If r=8 overfits (validation chrF degrades while training chrF improves), drop to r=4. If it underfits (both stay flat), step up to r=16 and add `gate_proj` and `up_proj` to `target_modules`.

### 4.3 Training Loop
- status: todo
- type: task
- id: ayoreo_translation.lora.train
- owner: researcher
- estimate: 1w
- blocked_by: [ayoreo_translation.lora.config]
<!-- content -->

Use Hugging Face `Seq2SeqTrainer` with the following non-default settings:

- **Effective batch size**: 32–64 via gradient accumulation. Larger batches stabilize gradients on small datasets.
- **Learning rate**: 3e-4 for LoRA params (LoRA learning rates are typically 10x higher than full-fine-tuning rates because the adapter starts from near-zero).
- **Warmup**: 6% of total steps.
- **Schedule**: cosine decay.
- **Epochs**: aim for a *budget* of 10–20 epochs but use early stopping on validation chrF with patience=3.
- **Evaluation cadence**: every 200 steps or every epoch, whichever comes first.
- **Label smoothing**: 0.1 — helps low-data generalization.
- **Save strategy**: best-checkpoint-only on validation chrF.

Direction handling: prepare the dataset with both directions interleaved. For NLLB, set source and target language tokens (`eng_Latn` and the appropriate Ayoreo language code if available, or treat Ayoreo as the closest related language code with a custom mapping documented in `experiments/lang_code_mapping.md`).

### 4.4 Checkpoint Selection and Adapter Export
- status: todo
- type: task
- id: ayoreo_translation.lora.export
- owner: researcher
- estimate: 1d
- blocked_by: [ayoreo_translation.lora.train]
<!-- content -->

Select the best checkpoint by validation chrF. Export only the adapter weights — typically 20–80 MB:

```python
model.save_pretrained("checkpoints/ayoreo_lora_v1")
# Save a sidecar manifest with the base-model ID and key hyperparameters,
# so a future loader doesn't need to spelunk through configs to reproduce.
```

Write `checkpoints/ayoreo_lora_v1/MODEL_CARD.md` documenting: base model, LoRA config, training data hash, training metrics, known failure modes. This is the artifact that goes into the inference pipeline.

## Phase 5 — Evaluation and Iteration
- status: todo
- type: task
- id: ayoreo_translation.eval
- owner: researcher
- estimate: 1w
- blocked_by: [ayoreo_translation.lora.export]
<!-- content -->

This phase is non-linear by design. The iteration loop may send us back to Phase 0 (more data), Phase 2 (tokenizer adjustments), or Phase 4 (different hyperparameters) depending on what error analysis reveals.

### 5.1 Automatic Evaluation
- status: todo
- type: task
- id: ayoreo_translation.eval.automatic
- owner: researcher
- estimate: 1d
<!-- content -->

Run the harness from 1.3 on the held-out test set. Compare against:

- RAG-only baseline (Phase 1.2)
- Zero-shot NLLB (no LoRA)
- Each Phase 4 checkpoint variation

Produce `experiments/eval_v1.json` and a small comparison plot. If LoRA does not beat the RAG baseline on chrF, do not proceed — go to 5.3 for diagnosis.

### 5.2 Human Evaluation
- status: todo
- type: task
- id: ayoreo_translation.eval.human
- owner: researcher
- estimate: 3d
<!-- content -->

For a sample of ~100 test sentences plus the full 50-sentence challenge set, collect adequacy/fluency/terminology ratings from at least one fluent Ayoreo speaker. Pay them; this is non-trivial labor.

Automatic metrics on low-resource languages are notoriously unreliable — a model that scores worse on chrF may translate better according to humans, and vice versa. Treat human evaluation as the source of truth and automatic metrics as a fast proxy.

### 5.3 Error Analysis and Iteration Decision
- status: todo
- type: task
- id: ayoreo_translation.eval.error_analysis
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.eval.automatic, ayoreo_translation.eval.human]
<!-- content -->

Categorize errors on a stratified sample of ~50 test outputs:

- **Lexical** — wrong word choice but grammar OK
- **Morphological** — wrong verb inflection, wrong agreement
- **Syntactic** — phrase ordering off
- **Hallucination** — content not in source
- **Copy failure** — proper nouns mangled
- **Domain shift** — works on register A, fails on register B

The dominant error category determines the next move:

- Lexical → add a terminology dictionary at inference (Phase 6.2)
- Morphological → revisit tokenizer (Phase 2), consider more pre-training (Phase 3)
- Hallucination → reduce LoRA rank or add more dropout (Phase 4.2)
- Domain shift → rebalance training mix (Phase 0)

Document the decision in `experiments/iteration_log.md` and loop back. After at most two full iterations, ship what we have and move to Phase 6 — perfectionism on this scale of data is a trap.

## Phase 6 — Hybrid Inference Pipeline
- status: todo
- type: task
- id: ayoreo_translation.inference
- owner: researcher
- estimate: 1w
- blocked_by: [ayoreo_translation.eval]
<!-- content -->

The end product. The trained LoRA model is one component of a three-stage inference pipeline; the hybrid setup substantially outperforms the model alone on extreme-low-resource settings.

### 6.1 LoRA Inference Service
- status: todo
- type: task
- id: ayoreo_translation.inference.lora_service
- owner: researcher
- estimate: 2d
<!-- content -->

Wrap the LoRA-adapted NLLB model as a service exposing a single `translate(text, src_lang, tgt_lang) -> str` function. Use beam search with `num_beams=5` and `length_penalty=1.0` as defaults; expose both as parameters.

Optimization: merge LoRA weights into the base model for inference (`model.merge_and_unload()`) — this removes the runtime overhead of the adapter side-path entirely.

### 6.2 Refinement Layer
- status: todo
- type: task
- id: ayoreo_translation.inference.refiner
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.inference.lora_service]
<!-- content -->

Compose: LoRA proposal → RAG retrieval of similar pairs → strong general LLM (Claude or GPT-4) refines for fluency and terminology. The LLM receives the source, the LoRA's proposed translation, and the retrieved examples, and is asked to produce a refined translation **constrained to stay close to the proposal**.

This pattern works because the LoRA model captures Ayoreo-specific patterns the LLM does not have, while the LLM catches fluency errors and terminology drift the LoRA model produces from limited data.

Also wire in a terminology dictionary lookup: for any proper noun, cultural term, or domain term in the source, inject its canonical Ayoreo form into the refiner prompt. This is the single highest-ROI inference-time intervention.

### 6.3 Confidence Scoring and Fallback
- status: todo
- type: task
- id: ayoreo_translation.inference.confidence
- owner: researcher
- estimate: 2d
- blocked_by: [ayoreo_translation.inference.refiner]
<!-- content -->

Surface confidence per output:

- Length-normalized sequence log-likelihood from the LoRA model.
- Agreement score between LoRA proposal and refiner output (high agreement = high confidence; large rewrites = the LoRA model was struggling).
- Retrieval similarity of the source to its nearest training neighbor (low similarity = out-of-distribution).

When confidence is below a tunable threshold, return the translation with a flag asking for human review rather than presenting it as authoritative. For a language with ~4,500 speakers, the cost of a confidently-wrong translation is high — calibrated humility matters.

## Phase 7 — Knowledge Capture
- status: todo
- type: task
- id: ayoreo_translation.kb_capture
- owner: researcher
- estimate: 3d
- blocked_by: [ayoreo_translation.inference]
<!-- content -->

Per convention rule 11, this plan must decide at design time what knowledge to capture in the KB. Three artifacts to produce:

- **New `how-to`**: `LOW_RESOURCE_TRANSLATION_LORA_SKILL.md` — a generalized procedure for LoRA fine-tuning on low-resource language pairs, with the Ayoreo run as the worked example. Scaffold this at `initial_draft` during Phase 4 and populate it as Phases 4–6 complete. This is `scope: general` — directly reusable for other low-resource language work.
- **New `reference`**: `AYOREO_ORTHOGRAPHY_REF.md` — the canonical orthographic-normalization decisions from Phase 0.3, with rationale. `scope: project-specific`.
- **New `explanation`**: `AYOREO_TOKENIZER_EXPLANATION.md` — why tokenizer fragmentation matters for low-resource MT, with the Phase 2 measurements as data. `scope: general`.

No existing KB document covers this territory closely enough to update; all three are new.

## Risk Register and Decision Points
- status: todo
- type: task
- id: ayoreo_translation.risks
- owner: researcher
- estimate: 0d
<!-- content -->

Standing risks, surfaced here so they are reviewed at every phase boundary:

- **Insufficient parallel data** (<500 clean pairs) — the most likely failure. Mitigation: the Phase 1 RAG baseline still produces a usable system without fine-tuning; if Phase 4 cannot beat it, ship Phase 1's output and document the gap.
- **No fluent Ayoreo speakers available for evaluation** — would invalidate Phase 5.2. Mitigation: establish at least one evaluator contact before Phase 4 begins; do not start training without one.
- **Catastrophic forgetting from continued pre-training** (Phase 3) — model loses multilingual competence in exchange for marginal Ayoreo gains. Mitigation: hold out a small set of base-model competency probes (e.g., Spanish→English translations) and check them before/after pre-training.
- **Community/ethical concerns about model deployment** — translation models for indigenous languages have a fraught history (extractive research, misrepresentation, loss of speaker agency). Mitigation: secure explicit community consent for both training data use and deployment; budget time for this before Phase 6.

## Open Questions
- status: todo
- type: task
- id: ayoreo_translation.open_questions
- owner: researcher
- estimate: 0d
<!-- content -->

Resolve before or during Phase 0 completion:

- What is the actual size of the cleaned parallel corpus? (Determines whether Phase 4 is viable at all.)
- Which Ayoreo orthographic convention does the speaker community prefer? (Phase 0.3 decision.)
- Is there a fluent speaker willing to participate in evaluation, and on what compensation terms?
- Are there community-imposed restrictions on what content domains the system should or should not translate?
- Is the Bolivian or Paraguayan Ayoreo variety the primary target? (They differ; mixing them in training without tagging is a known failure mode.)
