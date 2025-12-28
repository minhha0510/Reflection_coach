import networkx as nx
import json
from datetime import datetime
from graph_schema import (
    UserNode, BeliefNode, EventNode, Edge, EdgeType, NodeType
)

def run_prototype():
    print("Initializing Graph...")
    G = nx.DiGraph()

    # 1. Create Nodes
    user = UserNode(name="Test User", birth_year=1990)
    
    event_fail = EventNode(
        description="Failed a project at work",
        properties={"date": "2025-11-10"}
    )
    
    belief_neg = BeliefNode(
        text="I am incompetent",
        confidence=0.9,
        valence=-0.8,
        is_core=False
    )
    
    belief_core = BeliefNode(
        text="I must be perfect to be loved",
        confidence=1.0,
        valence=-0.5,
        is_core=True
    )

    # 2. Add Nodes to Graph
    # We use the node ID as the key, and store the object as a property
    nodes = [user, event_fail, belief_neg, belief_core]
    for n in nodes:
        G.add_node(n.id, **n.to_dict())

    print(f"Added {len(nodes)} nodes.")

    # 3. Add Edges
    # User EXPERIENCED Event
    edge1 = Edge(user.id, event_fail.id, EdgeType.EXPERIENCED)
    G.add_edge(edge1.source_id, edge1.target_id, **edge1.to_dict())

    # Event INTERPRETED_AS Belief (Negative)
    edge2 = Edge(event_fail.id, belief_neg.id, EdgeType.INTERPRETED_AS)
    G.add_edge(edge2.source_id, edge2.target_id, **edge2.to_dict())

    # Belief (Negative) EVOLVED_FROM Belief (Core) ?? Or maybe REINFORCES?
    # Let's say the negative belief is an expression of the core belief
    edge3 = Edge(belief_neg.id, belief_core.id, EdgeType.EVOLVED_FROM) # Or REINFORCES
    G.add_edge(edge3.source_id, edge3.target_id, **edge3.to_dict())

    print(f"Added {G.number_of_edges()} edges.")

    # 4. Traversal / Query
    print("\n--- Query: Why does the user feel incompetent? ---")
    # Find predecessors of the "I am incompetent" node
    
    # In a real app, we'd look up by text or embedding, here we use the object
    target_node_id = belief_neg.id
    
    predecessors = list(G.predecessors(target_node_id))
    for pred_id in predecessors:
        node_data = G.nodes[pred_id]
        edge_data = G.get_edge_data(pred_id, target_node_id)
        print(f"Cause Found: [{node_data['type']}] {node_data.get('description') or node_data.get('text')}")
        print(f"  -> Linked via: {edge_data['type']}")

    # 5. Serialization (Save to JSON)
    print("\n--- Serialization ---")
    data = nx.node_link_data(G)
    with open("graph_prototype.json", "w") as f:
        json.dump(data, f, indent=2)
    print("Graph saved to graph_prototype.json")

    # 6. Deserialization (Load back)
    print("\n--- Deserialization ---")
    with open("graph_prototype.json", "r") as f:
        data_loaded = json.load(f)
    
    G_loaded = nx.node_link_graph(data_loaded)
    print(f"Loaded Graph: {G_loaded.number_of_nodes()} nodes, {G_loaded.number_of_edges()} edges.")
    
    # Verify data integrity
    loaded_belief = G_loaded.nodes[belief_neg.id]
    print(f"Verified Node: {loaded_belief['text']} (Valence: {loaded_belief['valence']})")

if __name__ == "__main__":
    run_prototype()
