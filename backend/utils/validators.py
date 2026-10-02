import re
from utils.error_handler import ApiError

def text(value, label, limit=2000, required=False):
    if value is None: value = ""
    if not isinstance(value, str): raise ApiError(f"{label} must be text.")
    value = value.strip()
    if required and not value: raise ApiError(f"{label} is required.")
    if len(value) > limit: raise ApiError(f"{label} is too long.")
    return value

def skills(value):
    if isinstance(value, str): value = re.split(r"[,\n]", value)
    if not isinstance(value, list): raise ApiError("Skills must be a list or comma-separated text.")
    return list(dict.fromkeys(text(str(x), "Skill", 60) for x in value if str(x).strip()))[:60]
