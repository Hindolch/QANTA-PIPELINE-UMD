"""
Main CLI for converting Quizbowl tournament documents to QANTA format
"""

import argparse
import sys
from pathlib import Path
import json

from src.docx_parser import QuizbowlDocxParser
from src.answer_mapper import AnswerMapper
from src.sentence_splitter import SentenceSplitter
from src.qanta_converter import QantaConverter


def main():
    parser = argparse.ArgumentParser(
        description='Convert Quizbowl tournament documents to QANTA format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert a single DOCX file
  python convert_tournament.py --input "2025 PACE NSC Packets 2/Round 01.docx" --output data/output/2025_pace_r01.json
  
  # Convert all DOCX files in a directory
  python convert_tournament.py --input "2025 PACE NSC Packets 2/" --output data/output/2025_pace_all.json
  
  # Export as CSV
  python convert_tournament.py --input "2025 PACE NSC Packets 2/Round 01.docx" --output data/output/2025_pace_r01.csv --format csv
        """
    )
    
    parser.add_argument(
        '--input', '-i',
        type=str,
        required=True,
        help='Input DOCX file or directory containing DOCX files'
    )
    
    parser.add_argument(
        '--output', '-o',
        type=str,
        required=True,
        help='Output file path (.json, .csv, or .jsonl)'
    )
    
    parser.add_argument(
        '--format', '-f',
        type=str,
        choices=['json', 'jsonl', 'csv'],
        default='json',
        help='Output format (default: json)'
    )
    
    parser.add_argument(
        '--tournament-name',
        type=str,
        help='Tournament name for packet IDs (e.g., 2025_PACE_NSC)'
    )
    
    parser.add_argument(
        '--cache',
        type=str,
        help='Path to answer mapping cache file'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Parse but don\'t write output'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    
    args = parser.parse_args()
    
    # Validate input path
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input path does not exist: {args.input}", file=sys.stderr)
        return 1
    
    # Get list of DOCX files to process
    docx_files = []
    if input_path.is_file():
        if input_path.suffix.lower() == '.docx':
            docx_files = [input_path]
        else:
            print(f"Error: Input file must be .docx: {args.input}", file=sys.stderr)
            return 1
    else:
        docx_files = sorted(input_path.glob('*.docx'))
        if not docx_files:
            print(f"Error: No .docx files found in {args.input}", file=sys.stderr)
            return 1
    
    if args.verbose:
        print(f"Found {len(docx_files)} DOCX file(s) to process")
        for f in docx_files:
            print(f"  - {f.name}")
    
    # Initialize converter components
    try:
        answer_mapper = AnswerMapper(cache_file=args.cache)
        sentence_splitter = SentenceSplitter()
        converter = QantaConverter(answer_mapper, sentence_splitter)
    except ImportError as e:
        if "docx" in str(e):
            print("Error: python-docx not installed. Run: pip install python-docx", file=sys.stderr)
        else:
            print(f"Error: {e}", file=sys.stderr)
        return 1
    
    # Parse all documents
    all_questions = []
    parser_obj = QuizbowlDocxParser()
    
    for docx_file in docx_files:
        if args.verbose:
            print(f"\nProcessing: {docx_file.name}")
        
        try:
            raw_questions = parser_obj.parse_document(str(docx_file))
            
            # Generate packet ID
            if args.tournament_name:
                packet_id = f"{args.tournament_name}_{docx_file.stem}"
            else:
                packet_id = docx_file.stem  # e.g., "Round 01"
            
            # Convert questions
            converted = converter.convert_batch(raw_questions, packet_id)
            all_questions.extend(converted)
            
            if args.verbose:
                print(f"  Converted {len(converted)} questions")
        
        except Exception as e:
            print(f"Error processing {docx_file.name}: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    if not all_questions:
        print("Warning: No questions were parsed", file=sys.stderr)
    
    if args.verbose:
        print(f"\nTotal questions converted: {len(all_questions)}")
    
    # Save cache if using one
    if args.cache:
        answer_mapper.save_cache()
        if args.verbose:
            print(f"Saved answer cache to {args.cache}")
    
    # Export results
    if not args.dry_run:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if args.format == 'csv':
                converter.export_to_csv(all_questions, str(output_path))
            elif args.format == 'jsonl':
                converter.export_to_jsonl(all_questions, str(output_path))
            else:  # json
                converter.export_to_json(all_questions, str(output_path))
            
            if args.verbose:
                print(f"\nOutput saved to: {output_path}")
            else:
                print(f"Converted {len(all_questions)} questions and saved to {output_path}")
        
        except Exception as e:
            print(f"Error writing output: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
