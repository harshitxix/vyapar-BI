from datetime import datetime, timezone
from typing import Optional, Union
import dateutil.parser


def normalize_datetime(dt_input: Optional[Union[str, datetime, int, float]]) -> datetime:
    """
    Parses and converts any datetime input into a timezone-aware UTC datetime.
    Falls back to current UTC time if parsing fails or input is None.
    """
    if dt_input is None:
        return datetime.now(timezone.utc)

    if isinstance(dt_input, (int, float)):
        return datetime.fromtimestamp(dt_input, tz=timezone.utc)

    if isinstance(dt_input, datetime):
        if dt_input.tzinfo is None:
            return dt_input.replace(tzinfo=timezone.utc)
        return dt_input.astimezone(timezone.utc)

    if isinstance(dt_input, str):
        cleaned = dt_input.strip()
        if not cleaned:
            return datetime.now(timezone.utc)
        try:
            parsed = dateutil.parser.parse(cleaned)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)

    return datetime.now(timezone.utc)
