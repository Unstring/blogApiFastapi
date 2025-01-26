import random
import string
from datetime import datetime, timedelta
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def random_string(length=10):
    """Generate random string"""
    return ''.join(random.choices(string.ascii_letters, k=length))

def random_email():
    """Generate random email"""
    return f"{random_string(8).lower()}@{random_string(6).lower()}.com"

def random_password():
    """Generate valid random password"""
    return f"{random_string(6)}Aa1!"

def hash_password(password: str):
    """Hash password"""
    return pwd_context.hash(password)

def create_test_user(db, role="reader", password="Password123"):
    """Create test user with given role"""
    from models import User
    
    plain_password = password
    user = User(
        username=random_string(8),
        email=random_email(),
        password=hash_password(plain_password),
        role=role
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user, plain_password 