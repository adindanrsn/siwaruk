import re
import secrets
import string
from urllib.parse import quote
from flask import current_app
from app.models.user import User

REGISTER_MESSAGE = (
    "Halo Admin Siwaruk,\n\n"
    "Saya ingin mengajukan pembuatan akun Siwaruk.\n\n"
    "Nama:\n"
    "Nomor WhatsApp:\n\n"
    "Terima kasih."
)

FORGOT_PASSWORD_MESSAGE = (
    "Halo Admin Siwaruk,\n\n"
    "Saya mengalami kendala login dan ingin melakukan reset password.\n\n"
    "Username:\n"
    "Terima kasih."
)


CONSULTATION_MESSAGE = (
    "Halo Admin.\n\n"
    "Saya ingin berkonsultasi mengenai aplikasi Siwaruk.\n\n"
    "Mohon bantuannya.\n\n"
    "Terima kasih."
)


def normalize_whatsapp_number(phone: str) -> str:
    """
    Normalizes a phone number to standard Indonesian WhatsApp format (628...).
    Handles inputs like 0812..., 62812..., +62812...
    """
    if not phone:
        return ""

    # Remove all non-digit characters except leading plus
    digits = re.sub(r'\D', '', phone)

    if digits.startswith('0'):
        return '62' + digits[1:]
    elif digits.startswith('62'):
        return digits
    elif digits.startswith('8'):
        return '62' + digits

    return digits


def is_valid_whatsapp_number(phone: str) -> bool:
    """
    Validates if a phone number is a valid WhatsApp number.
    Must consist of digits (optional + prefix) and length between 9-15 chars.
    """
    if not phone:
        return False
    
    cleaned = re.sub(r'[\s\-]', '', phone)
    if cleaned.startswith('+'):
        cleaned = cleaned[1:]
    
    if not cleaned.isdigit():
        return False
        
    if len(cleaned) < 9 or len(cleaned) > 15:
        return False
        
    return True


def get_whatsapp_link(message_type: str) -> str:
    """
    Generate an encoded WhatsApp URL for contacting admin.

    :param message_type: 'register', 'forgot_password', or 'consultation'
    :return: Full WhatsApp URL string with pre-filled encoded text message.
    """
    import os
    env_wa = current_app.config.get('WHATSAPP_ADMIN') or os.getenv('WHATSAPP_ADMIN', '')

    if env_wa:
        wa_number = normalize_whatsapp_number(env_wa)
    else:
        admin_user = User.query.filter_by(role='admin').first()
        if not admin_user or not admin_user.phone:
            return ""
        wa_number = normalize_whatsapp_number(admin_user.phone)

    if message_type == "register":
        message_text = REGISTER_MESSAGE
    elif message_type == "forgot_password":
        message_text = FORGOT_PASSWORD_MESSAGE
    elif message_type in ["consultation", "floating"]:
        message_text = CONSULTATION_MESSAGE
    else:
        message_text = ""

    encoded_text = quote(message_text)
    return f"https://wa.me/{wa_number}?text={encoded_text}"


def generate_unique_username(full_name: str) -> str:
    """
    Generate a clean, unique username derived from the owner's full name.
    Example: 'Budi Santoso' -> 'budisantoso'.
    Appends incremental numbers if username exists ('budisantoso2', etc.).
    """
    base_username = re.sub(r'[^a-zA-Z0-9]', '', full_name.lower())
    if not base_username:
        base_username = "user"

    candidate = base_username
    counter = 2
    while User.query.filter_by(username=candidate).first() is not None:
        candidate = f"{base_username}{counter}"
        counter += 1

    return candidate


def generate_secure_password(length: int = 12) -> str:
    """
    Generate a random password using secrets module.
    Guarantees at least 1 uppercase letter, 1 lowercase letter, and 1 digit.
    Minimum length: 10.
    """
    if length < 10:
        length = 10

    uppercase = string.ascii_uppercase
    lowercase = string.ascii_lowercase
    digits = string.digits
    alphabet = uppercase + lowercase + digits

    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(length))
        if (any(c in uppercase for c in password) and
            any(c in lowercase for c in password) and
            any(c in digits for c in password)):
            return password


def get_active_business():
    """
    Get the currently active Business object for the logged-in owner from Flask session.
    Automatically initializes active_business_id if not set or invalid.
    """
    from flask import session
    from flask_login import current_user
    from app.models.business import Business

    if not current_user or not current_user.is_authenticated or current_user.role != 'owner':
        return None

    active_id = session.get('active_business_id')
    if active_id:
        biz = Business.query.filter_by(id=active_id, owner_id=current_user.id).first()
        if biz:
            return biz

    # Fallback to first business owned by the user
    first_biz = current_user.businesses.first()
    if first_biz:
        session['active_business_id'] = first_biz.id
        return first_biz

    session['active_business_id'] = None
    return None

