"""Supabase Storage utilities for file uploads."""
import io
import os
import logging
import zipfile
from datetime import datetime
from typing import Optional
import uuid

from utils.supabase_client import get_supabase_client, get_current_user_id

logger = logging.getLogger(__name__)

# Storage bucket name
BUCKET_NAME = 'attachments'


def upload_file(file_data: bytes, filename: str, fiscal_year: int) -> Optional[str]:
    """Upload a file to Supabase Storage.

    Args:
        file_data: File content as bytes
        filename: Original filename
        fiscal_year: Fiscal year for organizing files

    Returns:
        Storage path if successful, None otherwise
    """
    try:
        client = get_supabase_client()
        user_id = get_current_user_id()

        # Generate unique filename
        ext = os.path.splitext(filename)[1].lower()
        unique_id = uuid.uuid4().hex[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{unique_id}{ext}"

        # Create path: user_id/fiscal_year/filename
        if user_id:
            storage_path = f"{user_id}/{fiscal_year}/{safe_filename}"
        else:
            storage_path = f"anonymous/{fiscal_year}/{safe_filename}"

        # Determine content type
        content_type = 'application/octet-stream'
        if ext in ['.jpg', '.jpeg']:
            content_type = 'image/jpeg'
        elif ext == '.png':
            content_type = 'image/png'
        elif ext == '.pdf':
            content_type = 'application/pdf'
        elif ext == '.gif':
            content_type = 'image/gif'

        # Upload to Supabase Storage
        response = client.storage.from_(BUCKET_NAME).upload(
            path=storage_path,
            file=file_data,
            file_options={"content-type": content_type}
        )

        logger.info(f"File uploaded: {storage_path}")
        return storage_path

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return None


def get_file_url(storage_path: str, expires_in: int = 3600) -> Optional[str]:
    """Get a signed URL for a file in Supabase Storage.

    Args:
        storage_path: Path to the file in storage
        expires_in: URL expiration time in seconds (default 1 hour)

    Returns:
        Signed URL if successful, None otherwise
    """
    if not storage_path:
        return None

    try:
        client = get_supabase_client()

        # Generate signed URL
        response = client.storage.from_(BUCKET_NAME).create_signed_url(
            path=storage_path,
            expires_in=expires_in
        )

        if response and 'signedURL' in response:
            return response['signedURL']

        return None

    except Exception as e:
        logger.error(f"Error getting file URL: {e}")
        return None


def delete_file(storage_path: str) -> bool:
    """Delete a file from Supabase Storage.

    Args:
        storage_path: Path to the file in storage

    Returns:
        True if successful, False otherwise
    """
    if not storage_path:
        return False

    try:
        client = get_supabase_client()

        response = client.storage.from_(BUCKET_NAME).remove([storage_path])

        logger.info(f"File deleted: {storage_path}")
        return True

    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return False


def list_files(fiscal_year: int) -> list:
    """List all files for a fiscal year.

    Args:
        fiscal_year: Fiscal year to list files for

    Returns:
        List of file information dictionaries
    """
    try:
        client = get_supabase_client()
        user_id = get_current_user_id()

        if user_id:
            path = f"{user_id}/{fiscal_year}"
        else:
            path = f"anonymous/{fiscal_year}"

        response = client.storage.from_(BUCKET_NAME).list(path)

        return response if response else []

    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return []


def download_file(storage_path: str) -> Optional[bytes]:
    """Download a file from Supabase Storage.

    Args:
        storage_path: Path to the file in storage

    Returns:
        File content as bytes if successful, None otherwise
    """
    if not storage_path:
        return None

    try:
        client = get_supabase_client()
        response = client.storage.from_(BUCKET_NAME).download(storage_path)
        return response

    except Exception as e:
        logger.error(f"Error downloading file {storage_path}: {e}")
        return None


def download_all_attachments_as_zip(fiscal_year: int, attachments: list) -> Optional[bytes]:
    """Download all attachments for a fiscal year as a ZIP file.

    Files are organized by month (YYYY-MM/) with descriptive filenames.

    Args:
        fiscal_year: Fiscal year for the filename
        attachments: List of dicts with attachment_path, date, type, category, etc.

    Returns:
        ZIP file content as bytes if successful, None otherwise
    """
    if not attachments:
        return None

    try:
        # Create in-memory ZIP file
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            downloaded_count = 0
            used_names = set()

            for attachment in attachments:
                path = attachment.get('attachment_path') if isinstance(attachment, dict) else attachment
                if not path:
                    continue

                # Download file
                file_data = download_file(path)
                if not file_data:
                    logger.warning(f"Failed to download: {path}")
                    continue

                # Get file extension
                ext = os.path.splitext(path)[1].lower()

                # Build descriptive filename (flat structure)
                if isinstance(attachment, dict):
                    record_date = attachment.get('date', '')
                    record_type = attachment.get('type', '')
                    category = attachment.get('category', '')
                    client = attachment.get('client', '')

                    # Build descriptive filename
                    type_jp = '収入' if record_type == 'income' else '経費'
                    name_parts = [record_date, type_jp, category]
                    if client:
                        name_parts.append(client)
                    base_name = '_'.join(p for p in name_parts if p)

                    # Ensure unique filename
                    zip_path = f"{base_name}{ext}"
                    counter = 1
                    while zip_path in used_names:
                        zip_path = f"{base_name}_{counter}{ext}"
                        counter += 1
                    used_names.add(zip_path)
                else:
                    # Fallback for simple path list
                    zip_path = os.path.basename(path)

                zip_file.writestr(zip_path, file_data)
                downloaded_count += 1
                logger.debug(f"Added to ZIP: {zip_path}")

        if downloaded_count == 0:
            logger.warning("No files were downloaded")
            return None

        logger.info(f"Created ZIP with {downloaded_count} files for fiscal year {fiscal_year}")
        zip_buffer.seek(0)
        return zip_buffer.getvalue()

    except Exception as e:
        logger.error(f"Error creating ZIP file: {e}")
        return None
