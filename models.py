from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Table, func, select
from sqlalchemy.orm import relationship, column_property
from sqlalchemy.ext.declarative import declared_attr
from database import Base
from datetime import datetime
from sqlalchemy.orm import validates

# Define the association table for post-tag relationship
post_tags = Table(
    'post_tags',
    Base.metadata,
    Column('post_id', Integer, ForeignKey('posts.id', ondelete='CASCADE')),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'))
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String, default="reader")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")

    # Add role validation
    @validates('role')
    def validate_role(self, key, role):
        if role not in ('admin', 'author', 'reader'):
            raise ValueError("Role must be 'admin', 'author', or 'reader'")
        return role

class Status(Base):
    __tablename__ = "status"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(255))
    
    posts = relationship("Post", back_populates="status")

class Like(Base):
    __tablename__ = "likes"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    post = relationship("Post", back_populates="likes")
    user = relationship("User", back_populates="likes")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status_id = Column(Integer, ForeignKey('status.id', ondelete='SET NULL'), default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    author = relationship("User", back_populates="posts")
    status = relationship("Status", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=post_tags, back_populates="posts")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")

    # Fix the likes_count implementation
    likes_count = column_property(
        select(func.count(Like.id))
        .where(Like.post_id == id)
        .correlate_except(Like)
        .scalar_subquery()
    )

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    post_id = Column(Integer, ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    author_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = Column(DateTime, default=func.now())
    
    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    
    posts = relationship("Post", secondary=post_tags, back_populates="tags")