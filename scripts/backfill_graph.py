"""
Backfill Script: Ingest all existing daily reflections into the graph.

This script reads all .md files from the daily/ directory and processes them
through the ingestion pipeline to populate the reflection_graph.json.
"""

import os
import re
from graph_manager import GraphManager
from ingestion_pipeline import IngestionPipeline

def extract_conversation_from_md(filepath):
    """Extract the full conversation text from a markdown file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split by the "# Full Conversation" header
    parts = content.split('# Full Conversation', 1)
    if len(parts) > 1:
        return parts[1].strip()
    else:
        # If no header found, return everything after frontmatter
        parts = content.split('---', 2)
        if len(parts) > 2:
            return parts[2].strip()
        return content.strip()

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    daily_dir = os.path.join(script_dir, "daily")
    graph_path = os.path.join(script_dir, "reflection_graph.json")
    
    # Initialize Graph Components
    print("Initializing Graph Manager...")
    graph_manager = GraphManager(graph_path)
    ingestion_pipeline = IngestionPipeline(graph_manager)
    
    # Get all markdown files
    md_files = sorted([f for f in os.listdir(daily_dir) if f.endswith('.md')])
    
    if not md_files:
        print("No markdown files found in daily/ directory.")
        return
    
    print(f"\nFound {len(md_files)} reflection files to process.\n")
    
    # Process each file
    for i, filename in enumerate(md_files, 1):
        filepath = os.path.join(daily_dir, filename)
        print(f"[{i}/{len(md_files)}] Processing {filename}...")
        
        try:
            conversation = extract_conversation_from_md(filepath)
            
            if not conversation or len(conversation) < 50:
                print(f"  ⚠️  Skipped (conversation too short or empty)")
                continue
            
            # Ingest into graph
            ingestion_pipeline.process_session(conversation, session_id=filename)
            print(f"  ✅ Ingested ({len(conversation)} chars)")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    # Save the graph
    print("\nSaving graph...")
    graph_manager.save_graph()
    
    # Print summary
    total_nodes = len(graph_manager.graph.nodes())
    total_edges = len(graph_manager.graph.edges())
    print(f"\n{'='*50}")
    print(f"Backfill Complete!")
    print(f"Total Nodes: {total_nodes}")
    print(f"Total Edges: {total_edges}")
    print(f"Graph saved to: {graph_path}")
    print(f"{'='*50}\n")

if __name__ == "__main__":
    main()
