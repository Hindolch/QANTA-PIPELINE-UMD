# QANTA-2025 Tournament Converter

**A modular pipeline for converting modern Quizbowl packets into QANTA format**

This repository implements an end-to-end system for ingesting recent Quizbowl tournament packets (2024–2025), parsing them, mapping answers to canonical Wikipedia pages, splitting questions into sentences, and exporting them into the standardized **QANTA style CSV format**.

The goal is to make newer Quizbowl datasets easily usable for QA/IR/NLP research and compatible with existing QANTA pipelines.

---

## 🔍 Overview

The system processes a full tournament (e.g., 2025 PACE NSC) by:

1. **Parsing DOCX packets** into structured question objects
2. **Extracting and cleaning answers**
3. **Canonicalizing answers** using local wiki cache + Wikipedia search
4. **Splitting questions into sentences** (Quizbowl-aware)
5. **Attaching metadata** (packet, round, category, etc.)
6. **Exporting to QANTA-style CSV**
7. **Downloading Wikipedia article text** for each canonical page

All components are modular and can be reused or swapped.

---

## 🏗️ Project Structure

```
qb_converter/
│
├── batch_convert_all_rounds.py        # Orchestrates full DOCX → JSON → CSV pipeline
│
├── src/
│   ├── docx_parser.py                 # Parses .docx packets into raw question blocks
│   ├── sentence_splitter.py           # Splits question text into sentences
│   ├── answer_mapper.py               # Cleans answers + maps to canonical Wikipedia pages
│   ├── qanta_converter.py             # Combines all components → full question dicts
│   └── json_to_qanta.py               # Converts JSON → QANTA CSV + downloads wiki text
│
├── data/
│   ├── input/                         # DOCX tournament packets
│   ├── output/                        # Per-round JSON + CSV in QANTA format
│   └── wiki/                          # Local cache of downloaded Wikipedia articles
│
└── README.md
```

---

## 🚀 How It Works (High-Level Pipeline)

### 1. **DOCX Parsing**

`QuizbowlDocxParser` extracts:

* question text
* ANSWER line
* packet/round metadata
* question numbering

It normalizes noisy formatting across packets.

---

### 2. **Sentence Splitting**

`SentenceSplitter` performs Quizbowl-aware segmentation:

* preserves `|||` separators
* avoids splitting on abbreviations (Dr., Ph.D., etc.)
* removes the ANSWER line from the question body

Output: list of sentences.

---

### 3. **Answer Cleaning + Canonicalization**

`AnswerMapper` handles:

* stripping unnecessary parentheticals
* normalizing variants
* inferring broad category from keywords
* mapping to Wikipedia via:

  1. **local wiki cache**
  2. **Wikipedia API search** (top hit)

Results are cached to avoid repeated calls.

---

### 4. **JSON Export**

For each question, `QantaConverter` outputs:

```json
  {
    "qid": "Round 02",
    "question_num": 1,
    "packet": "Round 02",
    "raw_text": [...],
    "answer": "[ANSWER_NEEDS_MANUAL_REVIEW]",
    "answer_raw": "[ANSWER_NEEDS_MANUAL_REVIEW]",
    "sentences": [...],
    "category": "Misc",
    "wikipedia_page": null,
    "tournament": "Unknown",
    "year": 2025,
    "fold": "test",
    "date_added": "2025-11-26T11:00:05.218463"
  }
```

One JSON file per packet.

---

### 5. **QANTA CSV Export**

`json_to_qanta.py` converts JSON to QANTA-Compatible CSV with fields:

* Question ID
* Fold
* Answer
* Category
* Text


It also downloads and stores the Wikipedia article text in `data/wiki/`.

---

## 📦 Running the Pipeline

Place DOCX packets in:

```
data/input/
```

Then run:

```bash
python batch_convert_all_rounds.py \
    --input-dir data/input \
    --output-dir data/output \
    --wiki-dir data/wiki
```

This will:

* parse all packets
* generate JSON files
* generate QANTA CSVs
* download all Wikipedia article text

The converter outputs one JSON file and one QANTA CSV file per packet/round.
This design allows future tournaments (2024–2026+) to be added simply by placing DOCX files into data/input/.

---

## 📁 Output Example

```
data/output/
    round_01.json
    round_01_qanta.csv
    round_02.json
    round_02_qanta.csv
    ...
```

---

## 📘 Wikipedia Cache Format

Each article is stored as plain text:

```
data/wiki/
    Henry_IV_of_France.txt
    Impressionism.txt
    Treaty_of_Ghent.txt
```

This allows offline canonicalization and speeds up future runs.

---

## ⚠️ Limitations & Future Improvements

This is a functional and complete ingestion pipeline, but several components can be improved:

### 1. **Canonical Answer Mapping**

Current approach:

* normalizes answers
* checks local wiki cache
* uses top Wikipedia search result

Possible upgrades:

* resolve redirects (e.g., "Jean Valjean" → "Les Misérables")
* disambiguation ranking
* fuzzy title matching
* integrating WikiData properties

### 2. **Category Inference**

Currently keyword-based.
Could be upgraded to:

* Wikipedia categories
* Taxonomy mapping (Fine Arts → Literature, etc.)
* ML classifier trained on existing QANTA labels

### 3. **Sentence Splitter**

Works well for most packets, but rare cases may require:

* ML-based sentence segmentation (spaCy)
* Learned handling of Quizbowl conventions

These are left for future expansion.

---

## ✔️ Status

The pipeline works end-to-end for the full 2025 PACE NSC tournament (25 rounds):

* JSON conversion
* QANTA CSV generation
* Wikipedia text caching
* Metadata extraction
