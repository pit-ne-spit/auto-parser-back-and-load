"""Token generator for API tokens."""

import secrets
import string
from typing import List

from app.utils.logger import logger


def generate_token(length: int = 16) -> str:
    """
    Generate UUID-like token.
    
    Args:
        length: Token length (default 16)
        
    Returns:
        Random token string (letters and digits)
    """
    # Use letters (a-z, A-Z) and digits (0-9)
    alphabet = string.ascii_letters + string.digits
    token = ''.join(secrets.choice(alphabet) for _ in range(length))
    return token


def generate_tokens(count: int = 20, length: int = 16) -> List[str]:
    """
    Generate multiple unique tokens.
    
    Args:
        count: Number of tokens to generate
        length: Length of each token
        
    Returns:
        List of unique tokens
    """
    tokens = []
    seen = set()
    
    while len(tokens) < count:
        token = generate_token(length)
        if token not in seen:
            tokens.append(token)
            seen.add(token)
    
    logger.info(f"Generated {count} unique tokens (length: {length})")
    return tokens


def validate_token(token: str, length: int = 16) -> bool:
    """
    Validate token format.
    
    Args:
        token: Token to validate
        length: Expected token length
        
    Returns:
        True if token is valid, False otherwise
    """
    if not token or len(token) != length:
        return False
    
    # Check if token contains only letters and digits
    allowed_chars = string.ascii_letters + string.digits
    return all(c in allowed_chars for c in token)
