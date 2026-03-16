import asyncio
from app.utils.markdown_utils import escape_markdown_v2
text = "ตอนนี้มีกี่โปรเจ็คที่ active อยู่\n\n- Project A\n- Project_B"
final_text = escape_markdown_v2(text)
print(final_text)
