import argparse
import csv
import json
import os
import re
import hashlib
import urllib.parse
import urllib.request


"""Convert converter JSON output into QANTA-style CSV format.

Usage:
  python src/json_to_qanta.py --input data/output/round_01.json --output data/output/round_01_qanta.csv --wiki-dir data/wiki

This script:
- extracts the ANSWER: line from each question's `raw_text` or last sentence
- cleans the answer text
- infers category from the embedded tag in the question text (e.g. "<Author, Fine Arts - Jazz>")
- downloads and caches Wikipedia article texts to --wiki-dir for reference
- writes a CSV with columns: Question ID,Fold,Answer,Category,Text
  (matching the standard QANTA format in questions.csv)
"""

def extract_answer(raw_text, sentences=None):
    # Try to find an ANSWER: line in raw_text
    m = re.search(r'ANSWER:\s*(.+)$', raw_text, flags=re.IGNORECASE | re.MULTILINE)
    if m:
        ans = m.group(1).strip()
    elif sentences:
        # fallback to last sentence
        ans = sentences[-1].strip()
    else:
        return None

    # Remove editor/attribution tags trailing after '>' if present
    ans = re.sub(r"<.*$", "", ans).strip()

    # Remove surrounding parentheses and trailing period
    ans = ans.strip(' .\n\r')

    # If there are bracketed alternatives like [or ...], remove them
    ans = re.sub(r"\[.*?\]", "", ans).strip()

    # Remove parenthetical alternatives inside parentheses at end
    ans = re.sub(r"\([^)]*or[^)]*\)$", "", ans).strip()

    # Some answers include trailing qualifiers like '(prompt on ...)', remove them
    ans = re.sub(r"\(.*?prompt.*?\)", "", ans, flags=re.IGNORECASE).strip()

    # Normalize repeated whitespace
    ans = re.sub(r"\s+", " ", ans)

    # If answer contains 'ANSWER:' left over, remove it
    ans = re.sub(r'(?i)^ANSWER:\s*', '', ans).strip()

    return ans or None


def clean_answer_for_search(ans):
    # Remove clarifications like 'or', examples in brackets and punctuation
    s = ans
    # Convert 'AND' to 'and' for searches
    s = re.sub(r"\s+AND\s+", " and ", s)
    s = s.strip(' "')
    # Remove qualifiers after semicolon
    s = s.split(';')[0]
    return s


def find_local_wiki(ans, wiki_dir):
    if not wiki_dir:
        return None
    # Look for files with names matching common variants
    names = []
    base = ans
    names.append(base)
    names.append(base.replace(' ', '_'))
    names.append(base.title())
    names.append(base.replace(' & ', ' and '))

    # Normalize: remove punctuation
    base_simple = re.sub(r"[^A-Za-z0-9 _-]", '', base)
    names.append(base_simple)
    names.append(base_simple.replace(' ', '_'))

    files = os.listdir(wiki_dir) if os.path.isdir(wiki_dir) else []
    files_lower = {f.lower(): f for f in files}

    for n in names:
        key = n.strip().lower()
        if not key:
            continue
        cand = key + '.txt'
        if cand in files_lower:
            return files_lower[cand].rsplit('.', 1)[0]
        for f in files:
            if f.lower().endswith('.txt') and f.lower().rsplit('.txt', 1)[0] == key:
                return f.rsplit('.txt', 1)[0]

    return None


def wikipedia_search(ans):
    """Search Wikipedia for the answer and return the top page title."""
    query = ans
    if not query:
        return None
    url = 'https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch=' + urllib.parse.quote(query) + '&format=json&srlimit=1'
    req = urllib.request.Request(url, headers={'User-Agent': 'qb_converter/1.0 (contact: you@example.com) Python/3'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            import json as _json
            data = _json.load(resp)
            hits = data.get('query', {}).get('search', [])
            if hits:
                return hits[0]['title']
    except Exception:
        return None
    return None


def fetch_wikipedia_article(page_title, output_dir=None):
    """Fetch Wikipedia article text and save it to a local file."""
    if not page_title or not output_dir:
        return None
    
    url = 'https://en.wikipedia.org/w/api.php?action=query&titles=' + urllib.parse.quote(page_title) + '&prop=extracts&explaintext=true&format=json'
    req = urllib.request.Request(url, headers={'User-Agent': 'qb_converter/1.0 (contact: you@example.com) Python/3'})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            import json as _json
            data = _json.load(resp)
            pages = data.get('query', {}).get('pages', {})
            for page_id, page_data in pages.items():
                extract = page_data.get('extract')
                if extract:
                    os.makedirs(output_dir, exist_ok=True)
                    safe_filename = page_title.replace('/', '_').replace('\\', '_')
                    filepath = os.path.join(output_dir, safe_filename + '.txt')
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(extract)
                    print(f"  Saved: {safe_filename}.txt")
                    return extract
    except Exception as e:
        return None
    return None


def infer_category_from_raw(raw_text):
    # Look for a trailing tag like '<Author, Fine Arts - Jazz>' and extract category
    m = re.search(r'<[^,<>]+,\s*([^<>]+)>', raw_text)
    if m:
        cat = m.group(1).strip()
        parts = [p.strip() for p in re.split(r'\s*-\s*', cat) if p.strip()]
        if not parts:
            return 'Misc'
        top = parts[0].replace(' ', '_')
        if len(parts) > 1:
            sub = parts[1].replace(' ', '_')
            return f"{top}:{sub}"
        return top
    return None


def stable_int_id(s):
    h = hashlib.md5((s or '').encode('utf-8')).hexdigest()
    return str(int(h[:8], 16))


def process_file(input_path, output_path, wiki_dir=None, wiki_output_dir=None):
    with open(input_path, 'r', encoding='utf-8') as fh:
        data = json.load(fh)

    rows = []
    for idx, q in enumerate(data):
        qid = q.get('qid') or str(q.get('question_num') or '')
        qid_num = stable_int_id(qid)
        fold = q.get('fold', '')
        raw_text = q.get('raw_text', '')
        sentences = q.get('sentences', [])

        extracted = extract_answer(raw_text, sentences)
        answer_clean = None
        if extracted:
            answer_clean = extracted
            search_term = clean_answer_for_search(extracted)
            # Try local wiki dir first for reference caching
            wiki_page = find_local_wiki(search_term, wiki_dir) if wiki_dir else None
            if not wiki_page:
                api_title = wikipedia_search(search_term)
                if api_title:
                    # Fetch the Wikipedia article and save it locally for reference
                    if wiki_output_dir:
                        print(f"Q{idx+1}: Fetching {api_title}...")
                        fetch_wikipedia_article(api_title, wiki_output_dir)

        cat = infer_category_from_raw(raw_text) or q.get('category') or 'Misc'

        rows.append({
            'Question ID': qid_num,
            'Fold': fold,
            'Answer': answer_clean or '[ANSWER_NEEDS_MANUAL_REVIEW]',
            'Category': cat,
            'Text': raw_text.replace('\n', ' ').strip()
        })

    fieldnames = ['Question ID', 'Fold', 'Answer', 'Category', 'Text']
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return output_path


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--wiki-dir', default=None)
    p.add_argument('--wiki-output-dir', default=None)
    args = p.parse_args()

    out = process_file(args.input, args.output, wiki_dir=args.wiki_dir, wiki_output_dir=args.wiki_output_dir)
    print(f'Wrote {out}')


if __name__ == '__main__':
    main()
