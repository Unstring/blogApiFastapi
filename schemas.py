from pydantic import BaseModel, EmailStr, constr, validator, Field
from typing import List, Optional, Generic, TypeVar
from datetime import datetime
from enum import Enum
from config import settings

# Define a TypeVar for generic types
T = TypeVar('T')

# Enums
class UserRole(str, Enum):
    admin = "admin"
    author = "author"
    reader = "reader"

# Base User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    role: Optional[UserRole] = UserRole.reader

class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8)
    role: Optional[UserRole] = None

class User(UserBase):
    id: int
    role: UserRole
    created_at: datetime
    
    class Config:
        from_attributes = True

# Token schemas
class TokenData(BaseModel):
    username: str
    exp: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(default_factory=lambda: settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    user: User

    class Config:
        from_attributes = True

# Status schemas
class StatusBase(BaseModel):
    name: str
    description: str

class StatusCreate(StatusBase):
    pass

class Status(StatusBase):
    id: int

    class Config:
        from_attributes = True

# Tag schemas
class TagBase(BaseModel):
    name: str

class Tag(TagBase):
    id: int
    
    class Config:
        from_attributes = True

# Comment schemas
class CommentBase(BaseModel):
    content: str

class CommentCreate(CommentBase):
    pass

class Comment(CommentBase):
    id: int
    post_id: int
    author_id: int
    created_at: datetime
    author: User
    
    class Config:
        from_attributes = True

class CommentUpdate(BaseModel):
    content: str

    class Config:
        from_attributes = True

# Post schemas
class PostBase(BaseModel):
    title: str
    content: str
    status_id: Optional[int] = 1

class PostCreate(PostBase):
    tags: List[str] = []

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status_id: Optional[int] = None
    tags: Optional[List[str]] = None

class Post(PostBase):
    id: int
    author_id: int
    created_at: datetime
    updated_at: datetime
    status: Optional[Status] = None
    author: User
    tags: List[Tag] = []
    likes_count: int = 0
    
    class Config:
        from_attributes = True

# Like schemas
class LikeBase(BaseModel):
    post_id: int

class Like(LikeBase):
    id: int
    user_id: int
    created_at: datetime
    
    class Config:
        from_attributes = True

# Pagination schemas
class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    pages: int
    current_page: int
    items: List[T]

    class Config:
        from_attributes = True

# Add this to schemas.py
class PostWithLikeStatus(Post):
    is_liked: bool = False
    likes_count: int = 0

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    username: str
    password: str