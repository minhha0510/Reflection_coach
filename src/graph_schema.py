from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime

class NodeType(Enum):
    USER = "User"
    BELIEF = "Belief"
    EVENT = "Event"
    EMOTION = "Emotion"
    PERSON = "Person"
    TOPIC = "Topic"
    UTTERANCE = "Utterance"
    REFLECTION = "Reflection"
    DISTORTION = "Distortion"
    INQUIRY_THREAD = "InquiryThread"

class EdgeType(Enum):
    EXPERIENCED = "EXPERIENCED"       # User -> Event
    HAS_BELIEF = "HAS_BELIEF"         # User -> Belief
    TRIGGERED = "TRIGGERED"           # Event/Person -> Emotion
    INTERPRETED_AS = "INTERPRETED_AS" # Event -> Belief
    REINFORCES = "REINFORCES"         # Event -> Belief
    CONTRADICTS = "CONTRADICTS"       # Event -> Belief
    EVOLVED_FROM = "EVOLVED_FROM"     # Belief -> Belief
    SUPPRESSES = "SUPPRESSES"         # Belief -> Emotion
    EXPRESSED_IN = "EXPRESSED_IN"     # Belief -> Utterance
    FOCUSED_ON = "FOCUSED_ON"         # InquiryThread -> Topic
    PRECEDES = "PRECEDES"             # Event -> Event
    MENTIONS = "MENTIONS"             # Utterance -> Topic/Person/Event

@dataclass
class Node:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: NodeType = NodeType.USER # Default, should be overridden
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    valid_time_start: Optional[str] = None
    valid_time_end: Optional[str] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        from dataclasses import asdict
        data = asdict(self)
        # Convert Enum to string for JSON serialization
        data['type'] = self.type.value
        return data

@dataclass
class UserNode(Node):
    type: NodeType = NodeType.USER
    name: str = ""
    birth_year: Optional[int] = None

@dataclass
class BeliefNode(Node):
    type: NodeType = NodeType.BELIEF
    text: str = ""
    confidence: float = 1.0 # 0.0 to 1.0
    valence: float = 0.0 # -1.0 (Negative) to 1.0 (Positive)
    is_core: bool = False

@dataclass
class EventNode(Node):
    type: NodeType = NodeType.EVENT
    description: str = ""
    location: Optional[str] = None

@dataclass
class EmotionNode(Node):
    type: NodeType = NodeType.EMOTION
    label: str = "" # e.g. "Anxiety", "Joy"
    intensity: int = 5 # 1-10

@dataclass
class TopicNode(Node):
    type: NodeType = NodeType.TOPIC
    name: str = ""
    keywords: List[str] = field(default_factory=list)

@dataclass
class UtteranceNode(Node):
    type: NodeType = NodeType.UTTERANCE
    text: str = ""
    session_id: str = ""
    sequence_number: int = 0

@dataclass
class DistortionNode(Node):
    type: NodeType = NodeType.DISTORTION
    distortion_type: str = "" # e.g. "Catastrophizing"
    definition: str = ""

@dataclass
class InquiryThreadNode(Node):
    type: NodeType = NodeType.INQUIRY_THREAD
    status: str = "Active" # Active, Paused, Resolved
    goal: str = ""

@dataclass
class Edge:
    source_id: str
    target_id: str
    type: EdgeType
    weight: float = 1.0
    transaction_time: str = field(default_factory=lambda: datetime.now().isoformat())
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.type.value,
            "weight": self.weight,
            "transaction_time": self.transaction_time,
            **self.properties
        }
