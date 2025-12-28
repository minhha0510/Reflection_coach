import json
import os
import requests
from typing import List, Dict, Any
from dotenv import load_dotenv
from .graph_manager import GraphManager
from .graph_schema import (
    Node, UserNode, BeliefNode, EventNode, EmotionNode, 
    TopicNode, UtteranceNode, DistortionNode, 
    Edge, EdgeType, NodeType
)

load_dotenv()
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_URL = "https://api.deepseek.com/chat/completions"

EXTRACTION_SYSTEM_PROMPT = """
You are an expert Graph Database Architect and Psychoanalyst.
Your goal is to extract structured knowledge from a FULL CONVERSATION TRANSCRIPT to build a "Psyche Graph".

Input: A full dialogue between a User and a Coach.

Instructions:
1. Analyze the ENTIRE conversation as a whole.
2. Filter out:
   - Small talk ("Hello", "Thanks").
   - Transient thoughts that were immediately corrected or discarded.
   - Questions asked by the Coach (unless they reveal a specific User belief).
3. Extract SIGNIFICANT psychological entities (Nodes) and relationships (Edges).
   - Focus on recurring themes, core beliefs, strong emotions, and significant life events.
4. Detect Cognitive Distortions (e.g., "I always fail" -> All-or-Nothing).
5. Output ONLY valid JSON.

Schema Definitions:
- Nodes: User, Belief (Rules/Core Beliefs), Event (Episodes), Emotion, Person, Topic, Distortion (Cognitive Errors).
- Edges: EXPERIENCED, HAS_BELIEF, TRIGGERED (Event->Emotion), INTERPRETED_AS (Event->Belief), CONTRADICTS, REINFORCES, EVOLVED_FROM.

JSON Format:
{
  "nodes": [
    {"type": "Belief", "text": "I am not good enough", "valence": -0.8, "confidence": 0.9},
    {"type": "Event", "description": "Failed math test", "valid_time_start": "2023-05-01"},
    {"type": "Emotion", "label": "Shame", "intensity": 8}
  ],
  "edges": [
    {"source_index": 1, "target_index": 2, "type": "TRIGGERED"},
    {"source_index": 1, "target_index": 0, "type": "REINFORCES"}
  ]
}
Use "source_index" and "target_index" to refer to the position in the "nodes" array (0-indexed).
"""

class IngestionPipeline:
    def __init__(self, graph_manager: GraphManager):
        self.graph_manager = graph_manager

    def _call_llm(self, user_text: str) -> Dict[str, Any]:
        if not DEEPSEEK_API_KEY:
            print("Error: DEEPSEEK_API_KEY not set.")
            return {}

        messages = [
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ]

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature": 0.1, # Low temperature for structured output
            "response_format": {"type": "json_object"}
        }

        try:
            response = requests.post(DEEPSEEK_API_URL, headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"}, json=payload, timeout=120)
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            return json.loads(content)
        except Exception as e:
            print(f"Ingestion LLM Error: {e}")
            return {}

    def process_session(self, full_transcript: str, session_id: str = "default"):
        """
        Main entry point:
        1. Create Utterance Node for the *entire* session (or just link nodes to the session).
           *Design Choice*: We won't create a node for the whole text to save space, 
           but we will link extracted nodes to a Session ID if needed. 
           For now, we just extract the entities.
        2. Call LLM to extract graph elements from the full transcript.
        3. Create Nodes/Edges in GraphManager.
        """
        print(f"Ingesting Session ({len(full_transcript)} chars)...")
        
        # 1. Extract from full text
        data = self._call_llm(full_transcript)
        if not data:
            return

        extracted_nodes = []
        
        # 3. Create Extracted Nodes
        for n_data in data.get("nodes", []):
            node_type_str = n_data.get("type")
            new_node = None
            
            # Factory logic (simplified)
            if node_type_str == "Belief":
                new_node = BeliefNode(text=n_data.get("text"), valence=n_data.get("valence", 0), confidence=n_data.get("confidence", 1))
            elif node_type_str == "Event":
                new_node = EventNode(description=n_data.get("description"), valid_time_start=n_data.get("valid_time_start"))
            elif node_type_str == "Emotion":
                new_node = EmotionNode(label=n_data.get("label"), intensity=n_data.get("intensity", 5))
            elif node_type_str == "Topic":
                new_node = TopicNode(name=n_data.get("name"))
            elif node_type_str == "Distortion":
                new_node = DistortionNode(distortion_type=n_data.get("distortion_type"), definition=n_data.get("definition"))
            elif node_type_str == "Person":
                # Generic Node for now if class not fully fleshed out in factory
                # But we have Person in schema, let's assume we use generic Node or add PersonNode logic if needed
                # For now, map to Node with type PERSON
                new_node = Node(type=NodeType.PERSON, properties={"name": n_data.get("name")})
            
            if new_node:
                self.graph_manager.add_node(new_node)
                extracted_nodes.append(new_node)
                
                # Optional: Link to a Session Node if we had one.
                # For now, we just store the node.

        # 4. Create Edges between extracted nodes
        for e_data in data.get("edges", []):
            src_idx = e_data.get("source_index")
            tgt_idx = e_data.get("target_index")
            edge_type_str = e_data.get("type")
            
            if src_idx is not None and tgt_idx is not None and 0 <= src_idx < len(extracted_nodes) and 0 <= tgt_idx < len(extracted_nodes):
                src_node = extracted_nodes[src_idx]
                tgt_node = extracted_nodes[tgt_idx]
                
                try:
                    edge_type = EdgeType[edge_type_str] # Convert string to Enum
                    edge = Edge(src_node.id, tgt_node.id, edge_type)
                    self.graph_manager.add_edge(edge)
                except KeyError:
                    print(f"Unknown edge type: {edge_type_str}")

        print(f"Ingestion complete. Added {len(extracted_nodes)} nodes.")
