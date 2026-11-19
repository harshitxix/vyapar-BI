import hashlib
import re
from typing import Optional


def normalize_title(title: str) -> str:
    """
    Lowercases, removes special characters/punctuation, collapses whitespace,
    and strips leading/trailing characters.
    """
    if not title:
        return ""
    # Lowercase
    text = title.lower()
    # Remove HTML entities/tags if any
    text = re.sub(r"<[^>]+>", "", text)
    # Remove punctuation and special characters
    text = re.sub(r"[^\w\s]", " ", text)
    # Collapse multiple whitespaces
    text = re.sub(r"\s+", " ", text).strip()
    return text


def hash_normalized_title(title: str) -> str:
    """Generates SHA-256 hash of normalized title."""
    norm = normalize_title(title)
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def compute_content_fingerprint(title: str, description: Optional[str] = None) -> str:
    """
    Generates a 64-bit SimHash/fingerprint based on title + excerpt words.
    Used for lightweight near-duplicate detection in Phase 1.
    """
    text = normalize_title(title)
    if description:
        # Include first 200 chars of normalized description
        text += " " + normalize_title(description[:200])

    words = [w for w in text.split() if len(w) > 2]
    if not words:
        return hashlib.md5(text.encode("utf-8")).hexdigest()

    # 64-bit vector
    v = [0] * 64
    for word in words:
        # Hash each word to 64 bits
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        for i in range(64):
            bit = (h >> i) & 1
            if bit == 1:
                v[i] += 1
            else:
                v[i] -= 1

    fingerprint = 0
    for i in range(64):
        if v[i] > 0:
            fingerprint |= (1 << i)

    return f"{fingerprint:016x}"
