"""
Shipping field parser.

Two modes:
  1. JSON mode  — when OCR text is already a JSON object (OpenAI output).
  2. Regex mode — fallback for raw OCR text (Google Vision output).
"""

import json
import re
from typing import Dict

FIELD_KEYS = [
    "氏名",
    "郵便番号",
    "都道府県",
    "市区町村",
    "詳細住所",
    "電話番号",
    "配送方法",
    "送料",
    "商品名",
    "落札価格",
    "オークションID",
    "落札者ID",
]

_PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]


def parse(text: str) -> Dict[str, str]:
    """Parse OCR *text* and return a dict of shipping fields."""
    result = {k: "" for k in FIELD_KEYS}
    if not text.strip():
        return result

    # --- Try JSON first (structured output from OpenAI) ---
    json_str = _extract_json(text)
    if json_str:
        try:
            data = json.loads(json_str)
            for k in FIELD_KEYS:
                v = data.get(k, "")
                result[k] = str(v).strip() if v else ""
            return result
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

    # --- Fallback: regex parsing for raw OCR text ---
    return _regex_parse(text, result)


def check_status(fields: Dict[str, str]) -> str:
    """Return '需人工确认' if any critical address field is missing, else 'OK'."""
    critical = ["氏名", "郵便番号", "都道府県", "市区町村"]
    if any(not fields.get(k) for k in critical):
        return "需人工确认"
    return "OK"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> str:
    """Pull the first JSON object out of *text* (handles markdown code blocks)."""
    text = text.strip()
    if text.startswith("{"):
        return text
    # Markdown fenced block
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        return m.group(1)
    # Bare JSON object anywhere in text
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        return m.group(0)
    return ""


def _regex_parse(text: str, result: Dict[str, str]) -> Dict[str, str]:
    """Extract fields from raw OCR text using heuristic regex patterns."""

    # Postal code: 〒123-4567
    m = re.search(r"〒\s*(\d{3}[-ー]\d{4})", text)
    if not m:
        m = re.search(r"(?:郵便番号|郵便)[^\d]*(\d{3}[-ー]\d{4})", text)
    if m:
        result["郵便番号"] = m.group(1)

    # Prefecture + city
    for pref in _PREFECTURES:
        if pref in text:
            result["都道府県"] = pref
            m = re.search(
                re.escape(pref) + r"\s*([^\s\n]{2,15}(?:市|区|町|村))",
                text,
            )
            if m:
                result["市区町村"] = m.group(1)
            break

    # Name (after 氏名 / お名前 label)
    m = re.search(r"(?:氏名|お名前|お届け先氏名)[：:\s]+([^\n\d〒]{2,20})", text)
    if m:
        name = m.group(1).strip().rstrip("　 ")
        if 2 <= len(name) <= 20:
            result["氏名"] = name

    # Phone number
    m = re.search(r"(?:電話番号|TEL|Tel)[：:\s]*(\d{2,4}[-ー]\d{2,4}[-ー]\d{4})", text)
    if not m:
        m = re.search(r"(\d{2,4}-\d{2,4}-\d{4})", text)
    if m:
        result["電話番号"] = m.group(1)

    # Shipping method
    m = re.search(r"(?:配送方法|お届け方法)[：:\s]+([^\n]{2,30})", text)
    if m:
        result["配送方法"] = m.group(1).strip()

    # Shipping fee
    m = re.search(r"(?:送料|配送料)[：:\s]+([¥￥\d,，]+円?|無料|込み)", text)
    if m:
        result["送料"] = m.group(1).strip()

    # Product name
    m = re.search(r"(?:商品名|商品)[：:\s]*\n?([^\n]{2,80})", text)
    if m:
        result["商品名"] = m.group(1).strip()

    # Bid price
    m = re.search(r"(?:落札価格|落札金額)[：:\s]*([¥￥\d,，]+円?)", text)
    if m:
        result["落札価格"] = m.group(1).strip()

    # Auction ID (Yahoo format: letter + 9-11 digits, e.g. a123456789)
    m = re.search(
        r"(?:オークションID|オークション\s*ID)[：:\s]*([a-zA-Z0-9]{8,16})", text
    )
    if not m:
        m = re.search(r"\b([a-z]\d{9,11})\b", text)
    if m:
        result["オークションID"] = m.group(1)

    # Bidder ID
    m = re.search(
        r"(?:落札者|落札者ID|ご落札者)[：:\s]*([a-zA-Z0-9_\-\.]{3,30})", text
    )
    if m:
        result["落札者ID"] = m.group(1)

    return result
