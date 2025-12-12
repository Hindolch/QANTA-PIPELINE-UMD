import streamlit as st
import os
import sys
from pathlib import Path
import pandas as pd
import json
from batch_convert_all_rounds import (
    convert_docx_to_json,
    merge_csvs_into_dataset,
    push_to_huggingface
)
from src.json_to_qanta import process_file

# Page config
st.set_page_config(
    page_title="QANTA Tournament Converter",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .title-text { font-size: 2.5em; font-weight: bold; color: #1f77b4; }
    .subtitle-text { font-size: 1.2em; color: #666; }
    .success-box { background-color: #d4edda; padding: 1em; border-radius: 5px; }
    .error-box { background-color: #f8d7da; padding: 1em; border-radius: 5px; }
    .info-box { background-color: #d1ecf1; padding: 1em; border-radius: 5px; }
    </style>
""", unsafe_allow_html=True)

# Sidebar
st.sidebar.markdown("# ⚙️ Configuration")
st.sidebar.markdown("---")

# Main title
st.markdown('<p class="title-text">📚 QANTA Tournament Converter</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle-text">Convert Quizbowl tournaments to QANTA format with Wikipedia caching</p>', unsafe_allow_html=True)

# Tabs
tab1, tab2 = st.tabs(["🚀 Convert", "📊 Results"])

with tab1:
    st.markdown("## Step 1: Configure Paths")
    st.info("📌 **Tip:** Customize these paths for your tournament. Output/Wiki dirs will be created automatically.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        input_dir = st.text_input(
            "📁 Input Directory (DOCX packets)",
            value="./2025 PACE NSC Packets 2",
            help="Path to your tournament DOCX files (e.g., ./my_tournament_2024, ~/tournaments/nationals_2025)"
        )
    
    with col2:
        output_dir = st.text_input(
            "📁 Output Directory (CSV/JSON)",
            value="data/output",
            help="Where converted files will be saved. Created if it doesn't exist. E.g., ./my_tournament_2024/output"
        )
    
    with col3:
        wiki_dir = st.text_input(
            "📁 Wiki Cache Directory",
            value="data/wiki",
            help="Where Wikipedia articles are cached. Created if it doesn't exist. E.g., ./my_tournament_2024/wiki"
        )
    
    st.markdown("---")
    
    # Safety check: warn if output dir has existing data
    output_path = Path(output_dir)
    if output_path.exists():
        existing_csvs = list(output_path.glob('*_qanta.csv'))
        if existing_csvs:
            st.warning(f"⚠️ **WARNING:** Output directory already contains {len(existing_csvs)} CSV files!")
            col1, col2 = st.columns(2)
            with col1:
                backup_option = st.checkbox("🔄 Backup existing data before overwriting?", value=True)
            with col2:
                clear_option = st.checkbox("🗑️ Clear output directory first?", value=False)
            
            if backup_option or clear_option:
                st.info("✅ Backups/clearing will happen before conversion")
    
    st.markdown("## Step 2: Processing Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        verbose = st.checkbox("🔍 Verbose Output", value=True)
    
    with col2:
        push_hf = st.checkbox("🚀 Push to Hugging Face Hub", value=False)
    
    with col3:
        force_wiki = st.checkbox("♻️ Force Re-download Wiki Articles", value=False, 
                                help="Re-download and re-cache Wikipedia articles even if CSVs exist")
        
    # HF config (show only if push_hf is checked)
    if push_hf:
        st.markdown("### Hugging Face Configuration")
        col1, col2 = st.columns(2)
        
        with col1:
            hf_repo = st.text_input(
                "HF Repository ID(YOUR_USERNAME/REPO_NAME)",
                value="kenzi123/UMD-QANTA-PIPELINE",
                help="e.g., username/repo-name"
            )
        
        with col2:
            hf_token = st.text_input(
                "HF API Token",
                type="password",
                help="Your Hugging Face API token"
            )
    
    st.markdown("---")
    
    st.markdown("## Step 3: Execute Pipeline")
    
    # Start button
    if st.button("🎯 Start Conversion", key="start_btn", use_container_width=True):
        # Validate paths
        input_path = Path(input_dir)
        if not input_path.exists():
            st.error(f"❌ Input directory not found: {input_dir}")
            st.stop()
        
        docx_files = list(input_path.glob('*.docx'))
        if not docx_files:
            st.error(f"❌ No DOCX files found in {input_dir}")
            st.stop()
        
        # Safety: Backup or clear existing data
        output_path = Path(output_dir)
        if output_path.exists():
            existing_csvs = list(output_path.glob('*_qanta.csv'))
            if existing_csvs and (backup_option or clear_option):
                if backup_option:
                    from datetime import datetime
                    backup_dir = output_path / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    for csv_file in existing_csvs:
                        import shutil
                        shutil.copy(csv_file, backup_dir / csv_file.name)
                    st.success(f"✅ Backed up {len(existing_csvs)} files to {backup_dir.name}")
                
                if clear_option:
                    for csv_file in existing_csvs:
                        csv_file.unlink()
                    st.success(f"✅ Cleared {len(existing_csvs)} old CSV files")
        
        # Create output dirs if they don't exist
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        Path(wiki_dir).mkdir(parents=True, exist_ok=True)
        
        st.success(f"✅ Found {len(docx_files)} DOCX files")
        
        # Progress containers
        progress_container = st.container()
        status_container = st.container()
        
        with progress_container:
            st.markdown("### 📈 Progress")
            
            # Step 1: DOCX to JSON
            st.markdown("#### Step 1: Converting DOCX → JSON")
            progress_bar1 = st.progress(0)
            status_text1 = st.empty()
            
            success_count = 0
            for idx, docx_file in enumerate(docx_files):
                round_name = docx_file.stem
                json_output = Path(output_dir) / f'{round_name}.json'
                
                try:
                    convert_docx_to_json(str(docx_file), str(json_output), verbose=False)
                    success_count += 1
                except Exception as e:
                    status_text1.warning(f"⚠️ Error converting {round_name}: {e}")
                
                progress = (idx + 1) / len(docx_files)
                progress_bar1.progress(progress)
                status_text1.text(f"Progress: {success_count}/{len(docx_files)} converted")
            
            st.markdown(f"<div class='success-box'>✅ Step 1 Complete: {success_count}/{len(docx_files)} DOCX → JSON</div>", unsafe_allow_html=True)
            
            # Step 2: JSON to CSV with Wikipedia
            st.markdown("#### Step 2: Converting JSON → QANTA CSV (with Wikipedia)")
            json_files = sorted(Path(output_dir).glob('*.json'))
            json_files = [f for f in json_files if 'qanta' not in f.name]

            progress_bar2 = st.progress(0)
            status_text2 = st.empty()

            processed = 0
            for idx, json_file in enumerate(json_files):
                round_name = json_file.stem
                csv_output = Path(output_dir) / f'{round_name}_qanta.csv'
                
                # Skip if CSV exists AND force_wiki is False
                if csv_output.exists() and not force_wiki:
                    status_text2.info(f"⏭️ {round_name}_qanta.csv already exists, skipping...")
                    continue
                
                try:
                    status_text2.text(f"Processing {round_name}...")
                    process_file(
                        str(json_file),
                        str(csv_output),
                        wiki_dir=None,
                        wiki_output_dir=wiki_dir
                    )
                    processed += 1
                    status_text2.success(f"✓ {round_name} processed (wiki articles cached)")
                except Exception as e:
                    status_text2.warning(f"⚠️ Error processing {round_name}: {e}")
                
                progress = (idx + 1) / len(json_files)
                progress_bar2.progress(progress)

            st.markdown(f"<div class='success-box'>✅ Step 2 Complete: {processed} CSVs processed with Wikipedia caching</div>", unsafe_allow_html=True)
            
            # Step 3: Merge CSVs
            st.markdown("#### Step 3: Merging All CSVs")
            with st.spinner("Merging datasets..."):
                merged_csv = Path(output_dir) / '2025_pace_nsc_qanta.csv'
                try:
                    merge_csvs_into_dataset(str(Path(output_dir)), str(merged_csv))
                    st.markdown(f"<div class='success-box'>✅ Step 3 Complete: Merged dataset created</div>", unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"❌ Error merging CSVs: {e}")
            
            # Step 4: Push to HF (optional)
            if push_hf:
                st.markdown("#### Step 4: Pushing to Hugging Face")
                if not hf_token:
                    st.error("❌ Hugging Face token required")
                else:
                    with st.spinner("Uploading to Hugging Face..."):
                        try:
                            ok = push_to_huggingface(str(merged_csv), hf_repo, hf_token)
                            if ok:
                                st.markdown(f"<div class='success-box'>✅ Step 4 Complete: Dataset pushed to Hugging Face</div>", unsafe_allow_html=True)
                                hf_url = f"https://huggingface.co/datasets/{hf_repo}"
                                st.markdown(f"[🔗 View dataset on Hugging Face]({hf_url})")
                            else:
                                st.error("❌ Push to Hugging Face failed (check logs).")
                        except Exception as e:
                            st.error(f"❌ Error pushing to Hugging Face: {e}")
        
        st.markdown("---")
        
        # Show results
        st.markdown("### 📊 Results")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("DOCX Files", len(docx_files))
        
        with col2:
            csv_count = len(list(Path(output_dir).glob('*_qanta.csv')))
            st.metric("CSV Files", csv_count)
        
        with col3:
            wiki_count = len(list(Path(wiki_dir).glob('*.txt')))
            st.metric("Wikipedia Articles", wiki_count)
        
        with col4:
            if merged_csv.exists() and merged_csv.stat().st_size > 0:
                try:
                    df = pd.read_csv(merged_csv)
                    st.metric("Total Questions", len(df))
                except Exception as e:
                    st.warning(f"Could not read merged CSV: {e}")
            else:
                st.warning("Merged CSV is empty or missing")
        
        # Show preview of merged CSV
        if merged_csv.exists() and merged_csv.stat().st_size > 0:
            st.markdown("### 📋 Dataset Preview")
            try:
                df = pd.read_csv(merged_csv)
                st.dataframe(df.head(10), width='stretch')
            except Exception as e:
                st.error(f"Error displaying dataset preview: {e}")
            
            # Download button
            csv_content = df.to_csv(index=False)
            st.download_button(
                label="⬇️ Download Merged CSV",
                data=csv_content,
                file_name="2025_pace_nsc_qanta.csv",
                mime="text/csv"
            )

with tab2:
    st.markdown("## 📊 View Results")
    
    output_dir_display = st.text_input(
        "📁 Output Directory",
        value="data/output",
        key="display_output_dir"
    )
    
    output_path = Path(output_dir_display)
    
    if not output_path.exists():
        st.warning(f"Directory not found: {output_dir_display}")
        st.stop()
    
    # List CSV files
    csv_files = sorted(output_path.glob('*_qanta.csv'))
    
    if not csv_files:
        st.info("No CSV files found. Run the conversion first!")
    else:
        st.success(f"Found {len(csv_files)} CSV files")
        
        # Select file to view
        selected_csv = st.selectbox(
            "Select CSV to preview:",
            [f.name for f in csv_files]
        )
        
        if selected_csv:
            csv_path = output_path / selected_csv
            df = pd.read_csv(csv_path)
            
            st.markdown(f"### {selected_csv}")
            col1, col2, col3 = st.columns(3)
            col1.metric("Rows", len(df))
            col2.metric("Columns", len(df.columns))
            
            st.dataframe(df, width='stretch')
            
            # Download individual CSV
            csv_content = df.to_csv(index=False)
            st.download_button(
                label=f"⬇️ Download {selected_csv}",
                data=csv_content,
                file_name=selected_csv,
                mime="text/csv"
            )

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; font-size: 0.9em;">
📚 QANTA Tournament Converter v1.0 | Built with Streamlit | UMD Tryout Project
</div>
""", unsafe_allow_html=True)