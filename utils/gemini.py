"""Gemini API utilities for automatic data extraction from receipts."""
import os
import json
import base64
from typing import Optional
from google import genai
from google.genai import types
from PIL import Image
import io


# Encryption key (must match crypto.js)
_ENCRYPTION_KEY = 'TaxReturnApp2024SecureObfuscation'


def _xor_cipher(data: str, key: str) -> str:
    """XOR cipher for encryption/decryption."""
    result = []
    for i, char in enumerate(data):
        key_char = key[i % len(key)]
        result.append(chr(ord(char) ^ ord(key_char)))
    return ''.join(result)


def decrypt_api_key(encrypted_key: str) -> str:
    """
    Decrypt an API key that was encrypted by crypto.js.

    Args:
        encrypted_key: Base64-encoded encrypted API key

    Returns:
        Decrypted API key, or empty string if decryption fails
    """
    if not encrypted_key:
        return ''

    try:
        # Base64 decode
        decoded = base64.b64decode(encrypted_key).decode('utf-8')
        # XOR decrypt
        return _xor_cipher(decoded, _ENCRYPTION_KEY)
    except Exception:
        # If decryption fails, assume it's already plain text (legacy)
        return encrypted_key


def extract_from_image(image_data: bytes, api_key: str) -> dict:
    """
    Extract receipt/invoice information from an image using Gemini.

    Args:
        image_data: Image file bytes
        api_key: Gemini API key

    Returns:
        Dictionary with extracted fields
    """
    if not api_key:
        return {'error': 'Gemini APIキーが設定されていません', 'success': False}

    try:
        client = genai.Client(api_key=api_key)

        # 画像の MIME タイプを判定
        image = Image.open(io.BytesIO(image_data))
        mime_type = 'image/jpeg'
        if image.format == 'PNG':
            mime_type = 'image/png'
        elif image.format == 'GIF':
            mime_type = 'image/gif'
        elif image.format == 'WEBP':
            mime_type = 'image/webp'

        # Part オブジェクトとして画像を作成
        image_part = types.Part.from_bytes(data=image_data, mime_type=mime_type)

        prompt = """この画像は領収書、請求書、または経費関連の書類です。
以下の情報を抽出してJSON形式で返してください。

抽出する項目:
- date: 日付 (YYYY-MM-DD形式、不明な場合はnull)
- amount: 金額 (数値のみ、カンマなし)
- currency: 通貨 ("JPY" または "USD")
- client: 発行元/取引先名
- description: 内容/摘要
- category: 推測されるカテゴリ（以下から選択）
  - 収入の場合: "報酬", "給与", "その他収入"
  - 支出の場合: "通信費", "交通費", "消耗品費", "接待交際費", "地代家賃", "水道光熱費", "広告宣伝費", "新聞図書費", "支払手数料", "その他経費"
- type: 種別 ("income" または "expense"、推測)

必ず有効なJSONのみを返してください。余計な説明は不要です。

例:
{
  "date": "2024-03-15",
  "amount": 5500,
  "currency": "JPY",
  "client": "Amazon.co.jp",
  "description": "書籍購入",
  "category": "新聞図書費",
  "type": "expense"
}
"""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=[prompt, image_part]
        )

        # レスポンスからテキストを取得
        if hasattr(response, 'text'):
            response_text = response.text.strip()
        elif hasattr(response, 'candidates') and response.candidates:
            response_text = response.candidates[0].content.parts[0].text.strip()
        else:
            return {'error': f'予期しないレスポンス形式: {type(response)}', 'success': False}
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]

        result = json.loads(response_text.strip())

        # Gemini がリストを返す場合は最初の要素を使用
        if isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], dict):
                result = result[0]
            else:
                return {'error': '予期しないJSON形式（空のリスト）', 'success': False}

        result['success'] = True
        return result

    except json.JSONDecodeError as e:
        return {'error': f'JSON解析エラー: {str(e)}', 'success': False}
    except Exception as e:
        import traceback
        return {'error': f'Gemini API エラー: {str(e)}\n{traceback.format_exc()}', 'success': False}


def extract_from_pdf(pdf_data: bytes, api_key: str) -> dict:
    """
    Extract receipt/invoice information from a PDF using Gemini.

    Args:
        pdf_data: PDF file bytes
        api_key: Gemini API key

    Returns:
        Dictionary with extracted fields
    """
    if not api_key:
        return {'error': 'Gemini APIキーが設定されていません', 'success': False}

    tmp_path = None
    try:
        from PyPDF2 import PdfReader
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(pdf_data)
            tmp_path = tmp.name

        try:
            reader = PdfReader(tmp_path)
            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text() + "\n"
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if not text_content.strip():
            return {'error': 'PDFからテキストを抽出できませんでした', 'success': False}

        client = genai.Client(api_key=api_key)

        prompt = f"""以下は領収書、請求書、または経費関連の書類から抽出したテキストです。
以下の情報を抽出してJSON形式で返してください。

テキスト内容:
{text_content[:5000]}

抽出する項目:
- date: 日付 (YYYY-MM-DD形式、不明な場合はnull)
- amount: 金額 (数値のみ、カンマなし)
- currency: 通貨 ("JPY" または "USD")
- client: 発行元/取引先名
- description: 内容/摘要
- category: 推測されるカテゴリ（以下から選択）
  - 収入の場合: "報酬", "給与", "その他収入"
  - 支出の場合: "通信費", "交通費", "消耗品費", "接待交際費", "地代家賃", "水道光熱費", "広告宣伝費", "新聞図書費", "支払手数料", "その他経費"
- type: 種別 ("income" または "expense"、推測)

必ず有効なJSONのみを返してください。余計な説明は不要です。
"""

        response = client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )

        # レスポンスからテキストを取得
        if hasattr(response, 'text'):
            response_text = response.text.strip()
        elif hasattr(response, 'candidates') and response.candidates:
            response_text = response.candidates[0].content.parts[0].text.strip()
        else:
            return {'error': f'予期しないレスポンス形式: {type(response)}', 'success': False}
        if response_text.startswith('```json'):
            response_text = response_text[7:]
        if response_text.startswith('```'):
            response_text = response_text[3:]
        if response_text.endswith('```'):
            response_text = response_text[:-3]

        result = json.loads(response_text.strip())

        # Gemini がリストを返す場合は最初の要素を使用
        if isinstance(result, list):
            if len(result) > 0 and isinstance(result[0], dict):
                result = result[0]
            else:
                return {'error': '予期しないJSON形式（空のリスト）', 'success': False}

        result['success'] = True
        return result

    except json.JSONDecodeError as e:
        return {'error': f'JSON解析エラー: {str(e)}', 'success': False}
    except Exception as e:
        import traceback
        return {'error': f'Gemini API エラー: {str(e)}\n{traceback.format_exc()}', 'success': False}


def process_attachment(file_data: bytes, filename: str, api_key: str) -> dict:
    """
    Process an attachment and extract information.

    Args:
        file_data: File bytes
        filename: Original filename
        api_key: Gemini API key (may be encrypted)

    Returns:
        Dictionary with extracted fields
    """
    # Decrypt API key if encrypted
    decrypted_key = decrypt_api_key(api_key)

    ext = os.path.splitext(filename)[1].lower()

    if ext == '.pdf':
        return extract_from_pdf(file_data, decrypted_key)
    elif ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        return extract_from_image(file_data, decrypted_key)
    else:
        return {'error': f'サポートされていないファイル形式: {ext}', 'success': False}
