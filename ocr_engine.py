"""
OCR engine module — pluggable backend for image text extraction.

Supported engines:
  tongyi — Alibaba Tongyi Qianwen Vision (DashScope)
  doubao  — ByteDance Doubao Vision (Volcengine Ark)
"""

import base64
import io
import os
from abc import ABC, abstractmethod
from typing import Optional

from PIL import Image, ImageFilter, ImageEnhance

_EXTRACTION_PROMPT = """\
これはYahoo!オークション 取引ナビのスクリーンショットです。
以下のルールに従って各フィールドを抽出し、JSON形式のみで返してください。

【重要：氏名の抽出ルール】
- 氏名はお届け先の名称を抽出する（個人名または会社名）
- 個人名の場合：姓＋名のみ（例：山田太郎、佐藤花子）。通常2〜4文字の漢字
- 会社名の場合：株式会社・有限会社・合同会社などを含む正式名称をそのまま抽出
  （例：株式会社山田商事、山田商事株式会社）
- 視覚的に似た漢字を混同しないよう注意すること
  （例：「末」と「未」、「土」と「士」、「已」と「己」、「戊」と「戌」）
- 住所・落札者ID・数字は氏名に含めない
- 不確かな場合でも、最も可能性が高い読み方で出力する（空欄にしない）

その他のフィールド：
- 郵便番号: 〒マーク後の数字（例: 123-4567）
- 都道府県: 都道府県名のみ（例: 東京都、大阪府）
- 市区町村: 都道府県の次の市区町村名のみ（例: 新宿区、横浜市港北区）
- 詳細住所: 市区町村より後の番地・建物名
- 電話番号: お届け先の電話番号（例: 090-1234-5678）
- 配送方法: 配送・発送方法の名称（例: ゆうパック、ヤマト宅急便）
- 送料: 金額のみ（例: 600円、無料）
- 商品名: 落札された商品のタイトル（全文そのまま）
- 落札価格: 数字と円（例: 3,000円）
- オークションID: アルファベット+数字のID（例: a123456789）
- 落札者ID: 落札者のユーザーID

【抽出例】
入力画像に以下のような情報が含まれる場合：
　お届け先：山田 太郎　〒123-4567　東京都新宿区西新宿1-2-3
出力：
{
  "氏名": "山田太郎",
  "郵便番号": "123-4567",
  "都道府県": "東京都",
  "市区町村": "新宿区",
  "詳細住所": "西新宿1-2-3",
  "電話番号": "",
  "配送方法": "",
  "送料": "",
  "商品名": "",
  "落札価格": "",
  "オークションID": "",
  "落札者ID": ""
}

存在しない / 読み取れない項目は空文字 ("") にしてください。
JSONのみ出力してください。説明文・マークダウン記法は不要です。"""


def _preprocess_image(image_path: str) -> bytes:
    """Sharpen and enhance contrast before sending to Vision API."""
    img = Image.open(image_path).convert("RGB")

    # Upscale small images so text is clearer
    w, h = img.size
    if w < 1200:
        scale = 1200 / w
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    # Sharpen edges
    img = img.filter(ImageFilter.SHARPEN)
    img = img.filter(ImageFilter.SHARPEN)

    # Boost contrast slightly
    img = ImageEnhance.Contrast(img).enhance(1.3)

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()


class OCREngine(ABC):
    @abstractmethod
    def recognize(self, image_path: str) -> str:
        """Perform OCR on *image_path* and return extracted text as JSON."""


class DoubaoOCR(OCREngine):
    """ByteDance Doubao Vision — Volcengine Ark OpenAI-compatible endpoint."""

    _BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"

    def __init__(self, api_key: Optional[str] = None, model: str = "doubao-1-5-vision-pro-32k-250115"):
        import openai
        self._client = openai.OpenAI(
            api_key=api_key or os.environ.get("ARK_API_KEY", ""),
            base_url=self._BASE_URL,
        )
        self._model = model

    def recognize(self, image_path: str) -> str:
        b64 = base64.b64encode(_preprocess_image(image_path)).decode()
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": _EXTRACTION_PROMPT},
                ],
            }],
            max_tokens=1000,
        )
        return resp.choices[0].message.content or ""


class TongyiOCR(OCREngine):
    """Alibaba Tongyi Qianwen Vision — DashScope OpenAI-compatible endpoint."""

    _BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def __init__(self, api_key: Optional[str] = None, model: str = "qwen-vl-plus"):
        import openai
        self._client = openai.OpenAI(
            api_key=api_key or os.environ.get("DASHSCOPE_API_KEY", ""),
            base_url=self._BASE_URL,
        )
        self._model = model

    def recognize(self, image_path: str) -> str:
        b64 = base64.b64encode(_preprocess_image(image_path)).decode()
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": _EXTRACTION_PROMPT},
                ],
            }],
            max_tokens=1000,
        )
        return resp.choices[0].message.content or ""


def create_engine(engine_type: str = "tongyi", **kwargs) -> OCREngine:
    """Factory — returns an OCREngine instance for *engine_type*."""
    proxy = kwargs.pop("proxy", None)
    if proxy:
        for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                    "http_proxy", "https_proxy", "all_proxy"):
            os.environ[var] = proxy

    registry = {
        "doubao": DoubaoOCR,
        "tongyi": TongyiOCR,
    }
    cls = registry.get(engine_type.lower())
    if not cls:
        raise ValueError(f"Unknown engine '{engine_type}'. Available: {list(registry)}")
    return cls(**kwargs)
