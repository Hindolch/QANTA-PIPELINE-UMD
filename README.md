# QANTA-2025 Tournament Converter

**A modular, end-to-end pipeline for converting modern Quizbowl tournaments into QANTA format with automatic Hugging Face dataset upload**

This repository implements a complete system for ingesting recent Quizbowl tournament packets (2024–2025), parsing them, mapping answers to canonical Wikipedia pages, splitting questions into sentences, and exporting them into the standardized **QANTA CSV format** with automatic Hugging Face Hub integration.

The goal is to make newer Quizbowl datasets easily usable for QA/IR/NLP research, compatible with existing QANTA pipelines, and publicly accessible via Hugging Face Hub.

---

## 🔍 Overview

The system processes a full tournament (e.g., 2025 PACE NSC with 48 packets) by:

1. **Parsing DOCX packets** into structured question objects
2. **Extracting and cleaning answers**
3. **Canonicalizing answers** using local wiki cache + Wikipedia search
4. **Splitting questions into sentences** (Quizbowl-aware)
5. **Attaching metadata** (packet, round, category, etc.)
6. **Exporting to QANTA-style CSV** (one per round)
7. **Downloading Wikipedia article text** for each canonical page
8. **Merging all rounds** into a single dataset CSV
9. **(Optional) Pushing to Hugging Face Hub** for public access

All components are modular and can be reused or swapped.

---

## 🏗️ Project Structure

```
QANTA-PIPELINE-UMD/
│
├── batch_convert_all_rounds.py        # Orchestrates full pipeline: DOCX → JSON → CSV → merge → HF push
├── app.py        
│
├── src/
│   ├── docx_parser.py                 # Parses .docx packets into raw question blocks
│   ├── sentence_splitter.py           # Splits question text into sentences (Quizbowl-aware)
│   ├── answer_mapper.py               # Cleans answers + maps to canonical Wikipedia pages
│   ├── qanta_converter.py             # Combines all components → full question dicts
│   └── json_to_qanta.py               # Converts JSON → QANTA CSV + downloads wiki text
│
├── data/
│   ├── input/                         # Place DOCX packets here
│   ├── output/                        # Generated per-round JSON/CSV + merged dataset
│   │   └── 2025_pace_nsc_qanta.csv    # Final merged dataset (946 questions)
│   └── wiki/                          # Local cache of downloaded Wikipedia articles (1200+)
│
├── 2025 PACE NSC Packets 2/           # Input tournament packets (48 DOCX files)
│
├── requirements.txt
├── README.md
└── .env                               # HF_TOKEN for Hugging Face authentication
```

---

## 🚀 How It Works (High-Level Pipeline)

### Step 1: **DOCX Parsing**

`QuizbowlDocxParser` extracts:

* question text
* ANSWER line
* packet/round metadata
* question numbering

It normalizes noisy formatting across different packet styles.

Output: Raw question blocks in JSON format (one per round).

---

### Step 2: **Sentence Splitting**

`SentenceSplitter` performs Quizbowl-aware segmentation:

* preserves `|||` separators
* avoids splitting on abbreviations (Dr., Ph.D., etc.)
* removes the ANSWER line from the question body

Output: List of sentences per question.

---

### Step 3: **Answer Cleaning + Canonicalization**

`AnswerMapper` handles:

* stripping unnecessary parentheticals and brackets
* normalizing variants (e.g., "J.S. Bach" → "Johann Sebastian Bach")
* inferring broad category from question metadata
* mapping to Wikipedia via:

  1. **Local wiki cache** (fast, offline)
  2. **Wikipedia API search** (top hit with fallback)

Results are cached to avoid repeated API calls.

---

### Step 4: **JSON Export (Per-Round)**

For each question, `QantaConverter` outputs:

```json
{
  "qid": "Round 02",
  "question_num": 1,
  "packet": "Round 02",
  "raw_text": "This is the question text...",
  "answer": "Canonical Answer",
  "answer_raw": "original ANSWER: line",
  "sentences": ["Sentence 1.", "Sentence 2.", "..."],
  "category": "Literature:American",
  "wikipedia_page": "Some_Wikipedia_Page",
  "tournament": "2025_PACE_NSC",
  "year": 2025,
  "fold": "test",
  "date_added": "2025-12-01T12:00:00.000000"
}
```

One JSON file per packet.

---

### Step 5: **QANTA CSV Export (Per-Round)**

`json_to_qanta.py` converts JSON to QANTA-compatible CSV with columns:

* **Question ID** — unique identifier
* **Fold** — train/test/dev (default: "test")
* **Answer** — canonical answer
* **Category** — inferred from question metadata (e.g., "Literature:American")
* **Text** — full question text (sentences concatenated)

It also downloads and stores the Wikipedia article text in `data/wiki/`.

---

### Step 6: **Merging All Rounds**

`batch_convert_all_rounds.py` merges all per-round CSVs into a single dataset:

```
data/output/2025_pace_nsc_qanta.csv
```

This contains all 946 questions from 48 packets in QANTA format.

---

### Step 7: **(Optional) Push to Hugging Face Hub**

The pipeline can automatically upload the merged dataset to Hugging Face Hub:

```bash
python batch_convert_all_rounds.py \
    --input-dir "./2025 PACE NSC Packets 2" \
    --output-dir "data/output" \
    --wiki-dir "data/wiki" \
    --push-hf \
    --hf-repo "HF_USERNAME/YOUR_HF_DATASET_REPO_NAME"
```

This makes the dataset publicly accessible for researchers.

---

## 📦 Running the Pipeline

### Option 1: Convert Only (No Hugging Face Upload)

```bash
python batch_convert_all_rounds.py \
    --input-dir "./2025 PACE NSC Packets 2" \
    --output-dir "data/output" \
    --wiki-dir "data/wiki" \
    --verbose
```

Output:
* Per-round JSON files in `data/output/`
* Per-round CSV files in `data/output/`
* Merged dataset: `data/output/2025_pace_nsc_qanta.csv`
* Wikipedia articles in `data/wiki/`

---

### Option 2: Convert + Push to Hugging Face

First, set your Hugging Face token:

```bash
$env:HF_TOKEN="hf_xxxxx..."  # PowerShell
# OR
export HF_TOKEN="hf_xxxxx..."  # Linux/Mac
```

Then run:

```bash
python batch_convert_all_rounds.py \
    --input-dir "./2025 PACE NSC Packets 2" \
    --output-dir "data/output" \
    --wiki-dir "data/wiki" \
    --push-hf \
    --hf-repo "your-username/your-repo-name" \
    --verbose
```

The pipeline will:
1. Convert all DOCX → JSON
2. Convert all JSON → QANTA CSV
3. Download Wikipedia articles
4. Merge all CSVs into one
5. **Upload merged dataset to Hugging Face Hub**

---

## 📊 Tournament Statistics (2025 PACE NSC)

| Metric | Count |
|--------|-------|
| **Total Packets** | 48 |
| **Total Rounds** | 25 (regular) + tiebreakers + finals + emergency |
| **Total Questions** | 946 |
| **Questions Processed** | 946 |
| **Unique Wikipedia Pages** | 700+ |
| **Wikipedia Articles Cached** | 1200+ |
| **Output CSV Files** | 24 (per-round) + 1 (merged) |
| **Output JSON Files** | 24 (per-round) |
| **Merged Dataset Size** | ~946 rows (QANTA format) |

---

## 📁 Output Example

### Per-Round Outputs:
```
data/output/
    round_01.json
    round_01_qanta.csv
    round_02.json
    round_02_qanta.csv
    ...
    round_22_finals_1.json
    round_22_finals_1_qanta.csv
```

### Merged Dataset:
```
data/output/
    2025_pace_nsc_qanta.csv  (946 questions, QANTA format)
```

### Wikipedia Cache:
```
data/wiki/
    North_American_Free_Trade_Agreement.txt
    Henry_IV_of_France.txt
    Impressionism.txt
    ...
    (1200+ Wikipedia article texts)
```

---

## 📘 Example CSV Row

```csv
Question ID,Fold,Answer,Category,Text
3009,test,"Bella Hadid","Fine_Arts:Fashion","This American model and television personality, sister of the Weeknd collaborator Gigi, was born in Los Angeles in 1996. She has walked in shows for Chanel, Fendi, and others."
```

## HuggingFace dataset view 

<img width="1887" height="903" alt="Screenshot 2025-12-01 221843" src="https://github.com/user-attachments/assets/403570b6-6bc8-46c7-b8b8-ea484b229a26" />


---

## 🔧 Installation & Setup

### Prerequisites
- Python 3.8+
- `python-docx` (for DOCX parsing)
- `huggingface-hub` (for HF upload, optional)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Hugging Face (Optional)

Create a `.env` file in the repo root:

```
HF_TOKEN=hf_xxxxxxxxxxxxx
```

Or set the environment variable:

```bash
$env:HF_TOKEN="hf_xxxxx..."  # PowerShell
export HF_TOKEN="hf_xxxxx..."  # Linux/Mac
```

---

## ⚙️ Command-Line Options

```
usage: batch_convert_all_rounds.py [-h] 
    --input-dir INPUT_DIR 
    --output-dir OUTPUT_DIR 
    --wiki-dir WIKI_DIR 
    [--push-hf] 
    [--hf-repo HF_REPO] 
    [--hf-token HF_TOKEN]
    [--verbose]

options:
  --input-dir        Directory containing DOCX packets
  --output-dir       Directory to save JSON/CSV outputs
  --wiki-dir         Directory to cache Wikipedia articles
  --push-hf          Push merged CSV to Hugging Face Hub
  --hf-repo          Hugging Face repo ID (e.g., user/repo)
  --hf-token         Hugging Face token (env HF_TOKEN if omitted)
  --verbose          Print detailed progress
```

---

## 🖥️ Streamlit Web UI (optional)

A lightweight Streamlit frontend is included to run the entire pipeline from your browser. You can run the full pipeline either via the command-line interface or via this web UI — both perform the same DOCX → JSON → CSV → merge → (optional) Hugging Face upload workflow.

- Run from CLI:
  ```powershell
  python batch_convert_all_rounds.py --input-dir "./2025 PACE NSC Packets 2(./YOUR DATA FOLDER PATH)" --output-dir "data/output" --wiki-dir "data/wiki" --push-hf --hf-repo "your-username/your-repo-name"
  ```
- Run the Streamlit app:
  ```powershell
  streamlit run app.py
  ```

Features:
- Point-and-click configuration for Input / Output / Wiki cache directories
- Optional force re-download of Wikipedia articles
- Dynamic merged dataset filename
- Enter your Hugging Face repo ID + token to push the merged CSV to your account
- Shows a clickable Hugging Face dataset link after upload

Run the UI:

```powershell
pip install -r requirements.txt
streamlit run app.py
```

Default local URL: http://localhost:8501

Notes:
- The UI creates output/wiki directories automatically; it warns and can back up/clear existing outputs to avoid accidental overwrite.
- To push the merged CSV only, enable "Push to Hugging Face Hub", enter your HF repo (e.g. username/repo) and token — the app will display a link to the dataset after successful upload.

<img width="1906" height="960" alt="Screenshot 2025-12-12 125942" src="https://github.com/user-attachments/assets/34b9c170-f935-4cf6-897a-37e48fabbaa6" />

<img width="1908" height="797" alt="Screenshot 2025-12-12 141419" src="https://github.com/user-attachments/assets/4bd5e972-0192-4181-b9c9-4c7059a26d7f" />

<img width="1905" height="931" alt="Screenshot 2025-12-12 141501" src="https://github.com/user-attachments/assets/ddc56793-311a-44d9-b38d-df9ff9692fe4" />


---

## 📋 Limitations & Future Improvements

### 1. **Canonical Answer Mapping**

Current approach:
* Normalizes answers
* Checks local wiki cache
* Uses top Wikipedia search result

Possible upgrades:
* Resolve Wikipedia redirects
* Disambiguation ranking
* Fuzzy title matching
* WikiData entity linking

### 2. **Category Inference**

Currently keyword-based from question metadata.

Could be upgraded to:
* Wikipedia categories
* Taxonomy mapping
* ML classifier trained on QANTA labels

### 3. **Sentence Splitter**

Works well for most packets; edge cases may need:
* ML-based segmentation (spaCy)
* Learned Quizbowl conventions

---

## ✔️ Project Status

✅ **COMPLETE & PRODUCTION-READY**

- [x] DOCX parsing (all 48 packets)
- [x] JSON conversion (per-round)
- [x] QANTA CSV generation (per-round)
- [x] Wikipedia article caching (1200+)
- [x] Metadata extraction
- [x] CSV merging (single dataset)
- [x] Hugging Face integration
- [x] Full documentation
- [x] Modular, reusable code

The converter outputs **one JSON file and one QANTA CSV file per packet/round**, with a final merged dataset ready for distribution. This design allows future tournaments (2024–2026+) to be added simply by placing DOCX files into the input directory.

---

## 🔗 Links

- **Hugging Face:** https://huggingface.co/datasets/kenzi123/UMD-QANTA-PIPELINE
- **Original QANTA:** https://people.cs.umass.edu/~miyyer/qblearn/index.html

---

