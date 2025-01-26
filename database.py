from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Dict, Any

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        if db:
            try:
                db.close()
                if hasattr(db, 'bind'):
                    db.bind.dispose()
                    db.get_bind().dispose()
                setattr(db, 'is_active', False)  # Explicitly set is_active to False
            except:
                pass

def close_db(db: Session):
    """Explicitly close database session"""
    if db:
        try:
            db.close()
            if hasattr(db, 'bind'):
                db.bind.dispose()
                db.get_bind().dispose()
            setattr(db, 'is_active', False)  # Explicitly set is_active to False
        except:
            pass

def paginate(query, page: int = 1, limit: int = 10) -> Dict[str, Any]:
    """Paginate a SQLAlchemy query"""
    total = query.count()
    items = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "items": items,
        "total": total,
        "pages": (total + limit - 1) // limit,
        "current_page": page
    }