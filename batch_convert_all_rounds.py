import argparse
import sys
import os
import json
from pathlib import Path
from src.docx_parser import QuizbowlDocxParser
from src.answer_mapper import AnswerMapper
from src.sentence_splitter import SentenceSplitter
from src.qanta_converter import QantaConverter
from src.json_to_qanta import process_file

"""
Batch convert all tournament rounds: DOCX → JSON → QANTA CSV (with Wikipedia caching).

Usage:
  python batch_convert_all_rounds.py --input-dir "../2025 PACE NSC Packets 2/" --output-dir "data/output/" --wiki-dir "data/wiki/"

This script:
1. Converts each DOCX to JSON using the modular pipeline (parser → splitter → mapper → converter)
2. Converts each JSON to QANTA-format CSV and downloads Wikipedia articles for reference
3. Caches downloaded Wikipedia articles in --wiki-dir for offline inspection

Output format: QANTA-compatible CSV with columns:
  Question ID,Fold,Answer,Category,Text
  (Wikipedia articles are cached separately in data/wiki/ for reference)
"""

def convert_docx_to_json(docx_path, output_path, verbose=False):
    """Convert DOCX file to JSON using the modular converter pipeline."""
    try:
        # Initialize converter components
        answer_mapper = AnswerMapper()
        sentence_splitter = SentenceSplitter()
        converter = QantaConverter(answer_mapper, sentence_splitter)
        
        # Parse DOCX
        parser = QuizbowlDocxParser()
        raw_questions = parser.parse_document(str(docx_path))
        
        # Get packet ID from filename
        packet_id = Path(docx_path).stem  # e.g., "Round 01"
        
        # Convert questions
        converted_questions = converter.convert_batch(raw_questions, packet_id)
        
        # Write JSON
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(converted_questions, f, indent=2, ensure_ascii=False)
        
        if verbose:
            print(f"  ✓ {os.path.basename(docx_path)}: {len(converted_questions)} questions → {os.path.basename(output_path)}")
        
        return True
    except Exception as e:
        print(f"  ERROR converting {docx_path}: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False



def main():
    parser = argparse.ArgumentParser(
        description='Batch convert tournament rounds to QANTA format with Wikipedia downloads'
    )
    
    parser.add_argument(
        '--input-dir', '-i',
        type=str,
        required=True,
        help='Directory containing DOCX files (e.g., ../2025 PACE NSC Packets 2/)'
    )
    
    parser.add_argument(
        '--output-dir', '-o',
        type=str,
        required=True,
        help='Output directory for CSV files'
    )
    
    parser.add_argument(
        '--wiki-dir',
        type=str,
        required=True,
        help='Directory to store downloaded Wikipedia articles (e.g., data/wiki/)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    os.makedirs(args.output_dir, exist_ok=True)
    os.makedirs(args.wiki_dir, exist_ok=True)
    
    # Find all .docx files
    input_path = Path(args.input_dir)
    docx_files = sorted(input_path.glob('Round *.docx')) + sorted(input_path.glob('round *.docx'))
    
    if not docx_files:
        print(f"Error: No DOCX files found in {args.input_dir}")
        sys.exit(1)
    
    print(f"Found {len(docx_files)} DOCX files to process")
    
    # Step 1: Convert each DOCX to JSON using direct function calls
    print("\n=== Step 1: Converting DOCX files to JSON ===")
    success_count = 0
    for docx_file in docx_files:
        round_num = docx_file.stem.lower()
        json_output = os.path.join(args.output_dir, f'{round_num}.json')
        
        if convert_docx_to_json(str(docx_file), json_output, verbose=True):
            success_count += 1
    
    print(f"\nStep 1 complete: {success_count}/{len(docx_files)} DOCX files converted to JSON")
    
    # Step 2: Convert each JSON to QANTA CSV with Wikipedia downloads
    print("\n=== Step 2: Converting JSON to QANTA CSV (with Wikipedia downloads) ===")
    json_files = sorted(Path(args.output_dir).glob('round_*.json')) + sorted(Path(args.output_dir).glob('*.json'))
    
    skipped = 0
    processed = 0
    for json_file in json_files:
        if 'qanta' in json_file.name:
            continue
        
        round_name = json_file.stem
        csv_output = os.path.join(args.output_dir, f'{round_name}_qanta.csv')
        
        # Skip if CSV already exists
        if os.path.exists(csv_output):
            if args.verbose:
                print(f"  ⊘ {round_name}_qanta.csv (already exists, skipping)")
            skipped += 1
            continue
        
        if args.verbose:
            print(f"\nProcessing {json_file.name}...")
        
        process_file(
            str(json_file),
            csv_output,
            wiki_dir=None,  # Don't check local wiki dir, just download
            wiki_output_dir=args.wiki_dir
        )
        
        print(f"  ✓ {round_name}_qanta.csv")
        processed += 1
    
    if skipped > 0:
        print(f"\n  Skipped {skipped} CSVs (already exist)")
    print(f"  Processed {processed} new CSVs")
    
    print(f"\n Batch conversion complete!")
    print(f"   CSV files: {args.output_dir}")
    print(f"   Wiki files: {args.wiki_dir}")


if __name__ == '__main__':
    main()
