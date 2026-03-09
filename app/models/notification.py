from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class NotificationPayload(BaseModel):
    user_id: str
    message: str
    priority: str = Field("normal", pattern="^(high|normal)$")
    metadata: Optional[Dict[str, Any]] = None

    def get_formatted_message(self) -> str:
        """คืนค่าข้อความที่จัดรูปแบบตาม Priority (B)"""
        if self.priority == "high":
            return f"🚨 *IMPORTANT NOTIFICATION* 🚨\n\n{self.message}"
        return self.message

class NotificationResponse(BaseModel):
    status: str
    message: str
