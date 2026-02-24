"""
Auth Module — User registration, login, and password management.
Uses bcrypt for secure password hashing.
"""

import re
import bcrypt

from app_logger import logger


def hash_password(password: str) -> str:
    """Hash a password with bcrypt (salt rounds=12)."""
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def validate_password_strength(password: str) -> tuple:
    """
    Validate password meets minimum requirements.
    Returns: (is_valid: bool, error_message: str or None)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit"
    return True, None


def validate_username(username: str) -> tuple:
    """
    Validate username format.
    Returns: (is_valid: bool, error_message: str or None)
    """
    if len(username) < 3:
        return False, "Username must be at least 3 characters"
    if len(username) > 30:
        return False, "Username must not exceed 30 characters"
    if not re.match(r"^[a-zA-Z0-9_]+$", username):
        return False, "Username can only contain letters, numbers, and underscores"
    return True, None


# Generic error for security — never reveal which field is wrong
_LOGIN_FAILED_MSG = "Invalid email or password"


def register_user(conn, username: str, email: str, password: str):
    """
    Register a new user.

    Returns:
        dict: {"success": True, "user_id": id, "username": name} or {"success": False, "error": msg}
    """
    # Validate username
    valid, err = validate_username(username)
    if not valid:
        return {"success": False, "error": err}

    # Validate password strength
    valid, err = validate_password_strength(password)
    if not valid:
        return {"success": False, "error": err}

    cur = conn.cursor()

    # Check existing email
    cur.execute("SELECT id FROM users WHERE email = %s", (email.lower(),))
    if cur.fetchone():
        cur.close()
        return {"success": False, "error": "Email already registered"}

    # Check existing username
    cur.execute("SELECT id FROM users WHERE username = %s", (username,))
    if cur.fetchone():
        cur.close()
        return {"success": False, "error": "Username already taken"}

    # Hash password and create user
    pw_hash = hash_password(password)
    try:
        cur.execute(
            """
            INSERT INTO users (username, email, password_hash, total_xp, current_level, streak_days)
            VALUES (%s, %s, %s, 0, 1, 0)
            RETURNING id
            """,
            (username, email.lower(), pw_hash),
        )
        user_id = cur.fetchone()[0]

        # Create progress row for the new user
        cur.execute("INSERT INTO progress (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))

        conn.commit()
        logger.info("User registered: %s (ID: %d)", username, user_id)
        return {"success": True, "user_id": user_id, "username": username}

    except Exception as e:
        conn.rollback()
        logger.error("Registration failed: %s", str(e))
        return {"success": False, "error": "Registration failed. Please try again."}


def login_user(conn, email: str, password: str):
    """
    Authenticate a user by email and password.
    Uses generic error messages to prevent user enumeration attacks.

    Returns:
        dict: {"success": True, "user_id": id, "username": name} or {"success": False, "error": msg}
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password_hash FROM users WHERE email = %s",
        (email.lower(),),
    )
    row = cur.fetchone()

    if row is None:
        cur.close()
        logger.info("Login failed: email not found (not logged for security)")
        return {"success": False, "error": _LOGIN_FAILED_MSG}

    user_id, username, pw_hash = row

    if pw_hash is None:
        cur.close()
        return {"success": False, "error": _LOGIN_FAILED_MSG}

    if not verify_password(password, pw_hash):
        cur.close()
        logger.info("Login failed: incorrect password for user ID %d", user_id)
        return {"success": False, "error": _LOGIN_FAILED_MSG}

    # Update last_login timestamp
    try:
        cur.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s", (user_id,))
        conn.commit()
    except Exception:
        conn.rollback()

    cur.close()
    logger.info("User logged in: %s (ID: %d)", username, user_id)
    return {"success": True, "user_id": user_id, "username": username}


def get_user_by_id(conn, user_id: int):
    """Get user information by ID."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, email, total_xp, current_level, streak_days FROM users WHERE id = %s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()

    if row is None:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "email": row[2],
        "total_xp": row[3],
        "current_level": row[4],
        "streak_days": row[5],
    }
