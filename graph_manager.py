import networkx as nx
import json
import os
from typing import List, Optional, Dict, Any, Union
from graph_schema import (
    Node, Edge, NodeType, EdgeType,
    UserNode, BeliefNode, EventNode, EmotionNode, 
    TopicNode, UtteranceNode, DistortionNode, InquiryThreadNode
)

class GraphManager:
    def __init__(self, storage_path: str = "reflection_graph.json"):
        self.storage_path = storage_path
        self.graph = nx.DiGraph()
        self.load_graph()

    def load_graph(self):
        """Loads the graph from the JSON file if it exists."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r") as f:
                    data = json.load(f)
                self.graph = nx.node_link_graph(data)
                print(f"Graph loaded from {self.storage_path}: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")
            except Exception as e:
                print(f"Error loading graph: {e}. Starting with an empty graph.")
                self.graph = nx.DiGraph()
        else:
            print("No existing graph found. Starting fresh.")
            self.graph = nx.DiGraph()

    def save_graph(self):
        """Saves the current graph state to JSON."""
        data = nx.node_link_data(self.graph)
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Graph saved to {self.storage_path}")

    def add_node(self, node: Node):
        """Adds a node to the graph."""
        self.graph.add_node(node.id, **node.to_dict())
        self.save_graph() # Auto-save for now, can optimize later

    def add_edge(self, edge: Edge):
        """Adds an edge to the graph."""
        self.graph.add_edge(edge.source_id, edge.target_id, **edge.to_dict())
        self.save_graph()

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a node's data by ID."""
        if self.graph.has_node(node_id):
            return self.graph.nodes[node_id]
        return None

    def find_nodes_by_type(self, node_type: NodeType) -> List[Dict[str, Any]]:
        """Returns all nodes of a specific type."""
        results = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get("type") == node_type.value:
                results.append(data)
        return results

    def find_nodes_by_property(self, key: str, value: Any) -> List[Dict[str, Any]]:
        """Finds nodes where a specific property matches the value."""
        results = []
        for node_id, data in self.graph.nodes(data=True):
            if data.get(key) == value:
                results.append(data)
        return results

    def find_nodes_by_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Finds nodes where the 'text', 'description', 'label', or 'name' 
        contains the search text (case-insensitive).
        """
        results = []
        search_term = text.lower()
        for node_id, data in self.graph.nodes(data=True):
            # Check common text fields
            content = ""
            if "text" in data: content = data["text"]
            elif "description" in data: content = data["description"]
            elif "label" in data: content = data["label"]
            elif "name" in data: content = data["name"]
            
            if search_term in str(content).lower():
                results.append(data)
        return results

    def ego_walk(self, anchor_node_ids: List[str], depth: int = 2) -> str:
        """
        Performs the 'Ego Walk' traversal to generate context.
        1. Starts at anchor nodes.
        2. Expands to neighbors up to 'depth'.
        3. Prioritizes causal edges (TRIGGERED, REINFORCES, etc.).
        4. Returns a natural language summary of the subgraph.
        """
        if not anchor_node_ids:
            return "No relevant context found in graph."

        # BFS Traversal
        visited = set(anchor_node_ids)
        queue = [(nid, 0) for nid in anchor_node_ids]
        subgraph_nodes = set(anchor_node_ids)
        subgraph_edges = []

        while queue:
            current_id, current_depth = queue.pop(0)
            if current_depth >= depth:
                continue

            # Get neighbors
            neighbors = self.get_neighbors(current_id, direction="both")
            for item in neighbors:
                neighbor_node = item['node']
                neighbor_id = neighbor_node['id']
                edge_data = item['edge']
                
                # Add to subgraph
                subgraph_edges.append({
                    "source": current_id if item['direction'] == "outgoing" else neighbor_id,
                    "target": neighbor_id if item['direction'] == "outgoing" else current_id,
                    "type": edge_data['type']
                })
                subgraph_nodes.add(neighbor_id)

                if neighbor_id not in visited:
                    visited.add(neighbor_id)
                    queue.append((neighbor_id, current_depth + 1))

        return self._format_subgraph_as_text(subgraph_nodes, subgraph_edges)

    def _format_subgraph_as_text(self, node_ids: set, edges: List[Dict]) -> str:
        """Converts a subgraph into a narrative context string."""
        lines = []
        # Helper to get node label
        def get_label(nid):
            n = self.graph.nodes[nid]
            return n.get("text") or n.get("description") or n.get("label") or n.get("name") or "Unknown"

        lines.append(f"Graph Context ({len(node_ids)} nodes):")
        
        # List Nodes
        for nid in node_ids:
            n = self.graph.nodes[nid]
            ntype = n.get("type")
            label = get_label(nid)
            lines.append(f"- [{ntype}] {label}")

        # List Relationships
        lines.append("Relationships:")
        for e in edges:
            src_label = get_label(e['source'])
            tgt_label = get_label(e['target'])
            lines.append(f"- '{src_label}' --{e['type']}--> '{tgt_label}'")

        return "\n".join(lines)


    def get_neighbors(self, node_id: str, direction: str = "outgoing") -> List[Dict[str, Any]]:
        """Get neighboring nodes and the edges connecting them."""
        results = []
        if not self.graph.has_node(node_id):
            return results

        if direction == "outgoing" or direction == "both":
            for neighbor_id in self.graph.successors(node_id):
                edge_data = self.graph.get_edge_data(node_id, neighbor_id)
                node_data = self.graph.nodes[neighbor_id]
                results.append({
                    "node": node_data,
                    "edge": edge_data,
                    "direction": "outgoing"
                })
        
        if direction == "incoming" or direction == "both":
            for neighbor_id in self.graph.predecessors(node_id):
                edge_data = self.graph.get_edge_data(neighbor_id, node_id)
                node_data = self.graph.nodes[neighbor_id]
                results.append({
                    "node": node_data,
                    "edge": edge_data,
                    "direction": "incoming"
                })
        
        return results

    def get_user_node(self) -> Optional[Dict[str, Any]]:
        """Helper to find the singleton User node."""
        users = self.find_nodes_by_type(NodeType.USER)
        if users:
            return users[0]
        return None
