"""
Telegram Pydantic Models — รองรับ Telegram Bot API Update object

ใช้สำหรับ deserialize ข้อมูลที่ Telegram ส่งมาผ่าน Webhook
"""

from pydantic import BaseModel, Field
from typing import Optional


class TelegramUser(BaseModel):
    """ผู้ใช้ Telegram"""
    id: int
    is_bot: bool = False
    first_name: str = ""
    username: Optional[str] = None


class Chat(BaseModel):
    """Chat ที่ข้อความถูกส่งมา"""
    id: int
    type: str


class Message(BaseModel):
    """ข้อความจาก Telegram"""
    message_id: int
    chat: Chat
    from_user: Optional[TelegramUser] = Field(None, alias="from")
    date: int = 0
    text: Optional[str] = None


class CallbackQuery(BaseModel):
    """การกดปุ่ม Inline Keyboard"""
    id: str
    from_user: TelegramUser = Field(..., alias="from")
    message: Optional[Message] = None
    data: Optional[str] = None


class Update(BaseModel):
    """Telegram Update object — payload หลักที่ส่งมาทาง Webhook"""
    update_id: int
    message: Optional[Message] = None
    edited_message: Optional[Message] = None
    callback_query: Optional[CallbackQuery] = None
