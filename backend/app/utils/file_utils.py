import os
import re
import unicodedata

def is_pdf(filename: str) -> bool:
    """
    Returns True if the filename has a .pdf extension (case-insensitive).
    """
    _, ext = os.path.splitext(filename)
    return ext.lower() == ".pdf"

def sanitize_filename(filename: str) -> str:
    """
    Sanitizes a filename to prevent directory traversal attacks or filesystem issues.
    Extracts the base name, normalizes characters, and removes unsafe characters.
    """
    # Extract only the base name (no paths allowed)
    base_name = os.path.basename(filename)
    
    # Normalize unicode to ASCII representation
    normalized = unicodedata.normalize('NFKD', base_name).encode('ascii', 'ignore').decode('ascii')
    
    # Replace spaces and special characters with underscores, keeping alphanumeric, dashes, dots, and underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', normalized)
    
    # Replace multiple consecutive underscores or periods with a single one
    sanitized = re.sub(r'_+', '_', sanitized)
    sanitized = re.sub(r'\.+', '.', sanitized)
    
    # Trim leading/trailing dots or dashes which might be problematic on some systems
    sanitized = sanitized.strip('.-_')
    
    # Fallback to a default name if sanitization results in an empty string
    if not sanitized:
        sanitized = "unnamed_document.pdf"
        
    return sanitized
