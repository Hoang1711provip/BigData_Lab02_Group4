"""Small supplied helpers. They do not compute or certify data quality."""
import hashlib, json, uuid
from datetime import datetime, timezone
from pathlib import Path

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def ratio(numerator, denominator):
    if denominator == 0:
        return dict(n=numerator, d=0, value=None, status='NOT_EVALUATED')
    if not 0 <= numerator <= denominator:
        raise ValueError('Invalid numerator or denominator')
    return dict(n=numerator, d=denominator,
                value=numerator/denominator, status='EVALUATED')

def new_run():
    return str(uuid.uuid4())
