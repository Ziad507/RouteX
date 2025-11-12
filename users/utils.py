"""
Utility functions for users app.
"""


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number by extracting only digits.
    
    Args:
        phone: Raw phone number string
        
    Returns:
        String containing only digits from the input
    """
    return ''.join(ch for ch in (phone or '') if ch.isdigit())


def mask_phone(phone: str, show_first: int = 4, show_last: int = 2) -> str:
    """
    Mask phone number for privacy in API responses.
    
    Examples:
        "966500000013" -> "9665******13"
        "966512345678" -> "9665******78"
    
    Args:
        phone: Phone number string (digits only)
        show_first: Number of digits to show at the start (default: 4)
        show_last: Number of digits to show at the end (default: 2)
        
    Returns:
        Masked phone number string
    """
    if not phone:
        return phone
    
    phone_str = str(phone).strip()
    
    # If phone is too short, return as is
    if len(phone_str) <= show_first + show_last:
        return phone_str
    
    # Mask the middle part
    masked = phone_str[:show_first] + '*' * (len(phone_str) - show_first - show_last) + phone_str[-show_last:]
    
    return masked

