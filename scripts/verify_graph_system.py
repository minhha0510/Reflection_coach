import os
import time
from graph_manager import GraphManager
from ingestion_pipeline import IngestionPipeline
from graph_schema import NodeType

def verify_system():
    print("=== Starting Graph System Verification ===")
    
    # 1. Setup
    db_path = "test_graph.json"
    if os.path.exists(db_path):
        os.remove(db_path)
    
    gm = GraphManager(db_path)
    pipeline = IngestionPipeline(gm)

    # 2. Ingest Initial Fact (Batch Mode Simulation)
    print("\n[Test 1] Ingesting Full Session...")
    transcript = """
    User: I have a deep fear of public speaking because I failed a speech in high school.
    Coach: That sounds difficult. Can you tell me more?
    User: Tomorrow I have to give a presentation at work and I am feeling anxious.
    """
    pipeline.process_session(transcript)

    # 4. Test Retrieval (Ego Walk)
    print("\n[Test 3] Testing Ego Walk Retrieval...")
    # Simulate the agent looking for context on "presentation"
    anchors = gm.find_nodes_by_text("presentation")
    if not anchors:
        # Try "work" or "anxious" if presentation didn't create a node (depends on LLM)
        anchors = gm.find_nodes_by_text("anxious")
    
    if anchors:
        anchor_ids = [n['id'] for n in anchors]
        context = gm.ego_walk(anchor_ids)
        print(f"\n--- Generated Context ---\n{context}\n-------------------------")
        
        # Check if it pulled the "high school" memory (assuming LLM linked them or traversal found it)
        # Note: This depends on the LLM creating a link between "anxiety" and the previous "fear" or "public speaking"
        # If the LLM extraction is good, it might link 'anxiety' to 'public speaking' if it sees the connection, 
        # or if we query for 'public speaking' explicitly.
        
        if "high school" in context.lower() or "speech" in context.lower():
             print("✅ Context successfully retrieved past memory!")
        else:
             print("⚠️ Context might be missing deep links (depends on LLM extraction quality).")
    else:
        print("❌ No anchors found to walk.")

    # Debug: Print all nodes to see what was actually created
    print("\n[Debug] Current Graph Nodes:")
    for n in gm.graph.nodes(data=True):
        print(f" - {n[1].get('type')}: {n[1].get('text') or n[1].get('description') or n[1].get('label') or n[1].get('name')}")

    # 5. Persistence Check
    print("\n[Test 4] Verifying Persistence...")
    gm.save_graph()
    gm2 = GraphManager(db_path) # Reload
    if gm2.graph.number_of_nodes() == gm.graph.number_of_nodes():
        print(f"✅ Graph persisted correctly ({gm2.graph.number_of_nodes()} nodes).")
    else:
        print("❌ Persistence failure.")

    # Cleanup
    # if os.path.exists(db_path):
    #     os.remove(db_path)
    print("\n=== Verification Complete ===")

if __name__ == "__main__":
    verify_system()
