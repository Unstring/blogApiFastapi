from database import SessionLocal, Base, engine
from models import User, Status
from config import settings

def init_db():
    """Initialize database with required data"""
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Create admin user if it doesn't exist
        if not db.query(User).filter(User.role == "admin").first():
            admin = User(
                username="admin",
                email="admin@example.com",
                role="admin",
                password=settings.ADMIN_PASSWORD_HASH
            )
            db.add(admin)
        
        # Create default statuses if they don't exist
        default_statuses = [
            {"name": "draft", "description": "Draft post"},
            {"name": "published", "description": "Published post"}
        ]
        for status_data in default_statuses:
            if not db.query(Status).filter(Status.name == status_data["name"]).first():
                status = Status(**status_data)
                db.add(status)
        
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()