"""核心：連線、排隊、呼叫模型、驗證、清洗、儲存。功能請用這裡匯出的裝飾器登記。"""
from core.registry import Field, category, command, text_intent

__all__ = ["Field", "category", "command", "text_intent"]
