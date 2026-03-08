from dataclasses import dataclass, asdict
from typing import Optional
import datetime
import json

@dataclass
class AgentState:
    """Represents the last known working context of an agent for a specific project."""
    current_task: Optional[str] = None
    focus_file: Optional[str] = None
    last_activity_timestamp: Optional[datetime.datetime] = None
    version: int = 1

    def to_json(self) -> str:
        """Serializes the dataclass to a JSON string, handling datetime."""
        data = asdict(self)
        if self.last_activity_timestamp:
            data['last_activity_timestamp'] = self.last_activity_timestamp.isoformat()
        return json.dumps(data)

    @classmethod
    def from_json(cls, json_str: str) -> 'AgentState':
        """Deserializes a JSON string back to a dataclass instance."""
        data = json.loads(json_str)
        if 'last_activity_timestamp' in data and data['last_activity_timestamp']:
            data['last_activity_timestamp'] = datetime.datetime.fromisoformat(data['last_activity_timestamp'])
        return cls(**data)
