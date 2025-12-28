import os
import sys

# Ensure we can import from local directory
sys.path.append(os.getcwd())

from graph_manager import GraphManager
from ingestion_pipeline import IngestionPipeline

def regenerate_graph(file_path):
    print(f"Reading file: {file_path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Extract conversation part
    # The file has front matter, then "# Full Conversation", then the text.
    # We'll try to split by "# Full Conversation"
    parts = content.split("# Full Conversation")
    if len(parts) > 1:
        # Take the part after the header
        full_transcript = parts[1].strip()
    else:
        # Fallback to full content if header not found
        print("Warning: '# Full Conversation' header not found. Using full file content.")
        full_transcript = content

    print(f"Transcript length: {len(full_transcript)} chars")

    # Initialize Managers
    # Determine absolute path to reflection_graph.json to match ReflectionCoach
    script_dir = os.getcwd() 
    graph_path = os.path.join(script_dir, "reflection_graph.json")
    
    print(f"Loading graph from: {graph_path}")
    graph_manager = GraphManager(graph_path)
    ingestion_pipeline = IngestionPipeline(graph_manager)

    # Process
    print("Starting ingestion...")
    ingestion_pipeline.process_session(full_transcript)
    
    # Save
    graph_manager.save_graph()
    print("Regeneration complete and graph saved.")

if __name__ == "__main__":
    target_file = "daily/2025-12-23-122503.md"
    regenerate_graph(os.path.join(os.getcwd(), target_file))
