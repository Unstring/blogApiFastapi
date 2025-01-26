from typing import List, Optional
from fastapi import FastAPI, Depends, HTTPException, status, Request, Query, APIRouter
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from database import get_db, paginate
import models, schemas
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from config import settings
import re
from pydantic import BaseModel

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define the OAuth2PasswordBearerOptional class early in the file
class OAuth2PasswordBearerOptional(OAuth2PasswordBearer):
    """OAuth2 password bearer that makes token optional"""
    async def __call__(self, request: Request) -> Optional[str]:
        try:
            return await super().__call__(request)
        except HTTPException:
            return None

# Security setup
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearerOptional(tokenUrl=f"{settings.API_V1_PREFIX}/auth/login")

# Helper functions and dependencies
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def filter_published_posts(query, current_user=None):
    """Filter posts based on user authorization"""
    if not current_user:
        # Public users see only published posts
        return query.filter(models.Post.status_id == 2)  # 2 = published
    elif current_user.role == "admin":
        # Admins see all posts
        return query
    else:
        # Authors see all their own posts plus published posts from others
        return query.filter(
            or_(
                models.Post.author_id == current_user.id,  # All own posts
                models.Post.status_id == 2  # Published posts from others
            )
        )

async def get_current_user_optional(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
) -> Optional[models.User]:
    """Get current user if token provided, otherwise return None"""
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            return None
        user = db.query(models.User).filter(models.User.username == username).first()
        return user
    except JWTError:
        return None

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
        
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        raise credentials_exception
    return user

# Create the main router
router = APIRouter()

# Move the health check to router
@router.get("/health", tags=["system"])
async def health_check():
    """Check API health status"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }

@router.get("/", tags=["system"])
async def root():
    """API root endpoint with basic information"""
    return {
        "message": "Welcome to Blog API",
        "version": settings.VERSION,
        "docs": "/api/docs"
    }

# User routes
@router.get("/me", response_model=schemas.User, tags=["users"])
async def read_users_me(current_user: models.User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

@router.put("/me", response_model=schemas.User, tags=["users"])
async def update_user_profile(
    user_update: schemas.UserUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user profile"""
    try:
        # Check if username is being updated and is unique
        if user_update.username and user_update.username != current_user.username:
            if db.query(models.User).filter(models.User.username == user_update.username).first():
                raise HTTPException(status_code=400, detail="Username already taken")
            current_user.username = user_update.username

        # Check if email is being updated and is unique
        if user_update.email and user_update.email != current_user.email:
            if db.query(models.User).filter(models.User.email == user_update.email).first():
                raise HTTPException(status_code=400, detail="Email already registered")
            current_user.email = user_update.email

        # Update password if provided
        if user_update.password:
            if not validate_password(user_update.password):
                raise HTTPException(
                    status_code=400,
                    detail="Password must be at least 8 characters and contain uppercase, lowercase, and numbers"
                )
            current_user.password = get_password_hash(user_update.password)

        db.commit()
        db.refresh(current_user)
        return current_user
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating user profile: {e}")
        raise HTTPException(status_code=500, detail="Could not update profile")

@router.get("/me/posts", response_model=schemas.PaginatedResponse[schemas.Post])
async def list_user_posts(
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """List posts for current user"""
    query = db.query(models.Post).filter(models.Post.author_id == current_user.id)
    total = query.count()
    posts = query.order_by(models.Post.created_at.desc())\
                .offset((page - 1) * limit)\
                .limit(limit)\
                .all()
    
    return {
        "items": posts,
        "total": total,
        "pages": (total + limit - 1) // limit,
        "current_page": page
    }

@router.get("/me/comments", response_model=schemas.PaginatedResponse[schemas.Comment], tags=["users"])
async def list_user_comments(
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all comments by current user"""
    query = db.query(models.Comment).filter(models.Comment.author_id == current_user.id)
    total = query.count()
    comments = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "pages": (total + limit - 1) // limit,
        "current_page": page,
        "items": comments
    }

@router.get("/me/likes", response_model=schemas.PaginatedResponse[schemas.Post], tags=["users"])
async def list_user_liked_posts(
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all posts liked by current user"""
    query = db.query(models.Post).join(models.Like).filter(models.Like.user_id == current_user.id)
    total = query.count()
    posts = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "pages": (total + limit - 1) // limit,
        "current_page": page,
        "items": posts
    }

# Public routes for posts
@router.get("/posts", response_model=schemas.PaginatedResponse[schemas.Post], tags=["posts"])
async def list_posts(
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional)
):
    """List all published posts with optional search"""
    query = db.query(models.Post)
    
    # Apply visibility rules
    if not current_user:
        query = query.filter(models.Post.status_id == 2)  # Only published posts
    elif current_user.role == "admin":
        pass  # Admin sees all posts
    else:
        # Users see their own posts and published posts
        query = query.filter(
            or_(
                models.Post.author_id == current_user.id,
                models.Post.status_id == 2
            )
        )

    if search:
        query = query.filter(
            or_(
                models.Post.title.ilike(f"%{search}%"),
                models.Post.content.ilike(f"%{search}%")
            )
        )
    
    return paginate(query.order_by(models.Post.created_at.desc()), page, limit)

@router.get("/posts/{post_id}", response_model=schemas.Post, tags=["posts"])
async def get_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional)
):
    """Get a specific post"""
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check visibility rules
    if post.status_id != 2:  # If not published
        if not current_user:  # If no user logged in
            raise HTTPException(status_code=404, detail="Post not found")
        if current_user.role != "admin" and current_user.id != post.author_id:
            # If not admin and not author
            raise HTTPException(status_code=404, detail="Post not found")
    
    return post

@router.get("/posts/{post_id}/comments", response_model=List[schemas.Comment], tags=["comments"])
async def list_post_comments(post_id: int, db: Session = Depends(get_db)):
    """List comments for a post"""
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post or post.status_id != 2:  # Only show comments on published posts
        raise HTTPException(status_code=404, detail="Post not found")
    return post.comments

@router.get("/users/{user_id}", response_model=schemas.User, tags=["users"])
async def get_user_profile(user_id: int, db: Session = Depends(get_db)):
    """Get user profile"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("/status", response_model=List[schemas.Status], tags=["system"])
async def list_status(db: Session = Depends(get_db)):
    """List all post statuses"""
    return db.query(models.Status).all()

@router.get("/tags", response_model=List[schemas.Tag], tags=["tags"])
async def list_tags(db: Session = Depends(get_db)):
    """List all tags"""
    return db.query(models.Tag).all()

@router.get("/posts/{post_id}/likes", response_model=int, tags=["likes"])
async def get_post_likes(post_id: int, db: Session = Depends(get_db)):
    """Get number of likes for a post"""
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return db.query(models.Like).filter(models.Like.post_id == post_id).count()

@router.post("/posts", response_model=schemas.Post, status_code=201, tags=["posts"])
async def create_post(
    post: schemas.PostCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new blog post"""
    try:
        # Verify status exists
        status = db.query(models.Status).filter(models.Status.id == post.status_id).first()
        if not status:
            raise HTTPException(status_code=404, detail="Status not found")

        # Create post
        db_post = models.Post(
            **post.model_dump(exclude={'tags'}),
            author_id=current_user.id
        )
        db.add(db_post)
        db.flush()
        
        # Handle tags
        for tag_name in post.tags:
            tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
            if not tag:
                tag = models.Tag(name=tag_name)
                db.add(tag)
                db.flush()
            db_post.tags.append(tag)
        
        db.commit()
        db.refresh(db_post)
        return db_post
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating post: {e}")
        if "Status not found" in str(e):
            raise HTTPException(status_code=404, detail="Status not found")
        raise HTTPException(status_code=500, detail="Could not create post")

@router.put("/posts/{post_id}", response_model=schemas.Post, tags=["posts"])
async def update_post(
    post_id: int,
    post_update: schemas.PostUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update a specific post"""
    # Get existing post
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check authorization
    if not check_resource_permission(current_user, db_post.author_id, "edit"):
        raise NotAuthorizedError("edit")

    try:
        # Update basic fields
        update_data = post_update.dict(exclude_unset=True, exclude={'tags'})
        for field, value in update_data.items():
            setattr(db_post, field, value)

        # Update tags if provided
        if post_update.tags is not None:
            db_post.tags = []
            for tag_name in post_update.tags:
                tag = db.query(models.Tag).filter(models.Tag.name == tag_name).first()
                if not tag:
                    tag = models.Tag(name=tag_name)
                    db.add(tag)
                    db.flush()
                db_post.tags.append(tag)

        db.commit()
        db.refresh(db_post)
        return db_post
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating post: {e}")
        raise HTTPException(status_code=500, detail="Could not update post")

@router.delete("/posts/{post_id}", status_code=200, tags=["posts"])
async def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a specific post"""
    db_post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not db_post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check authorization
    if not check_resource_permission(current_user, db_post.author_id, "delete"):
        raise NotAuthorizedError("delete")

    try:
        db.delete(db_post)
        db.commit()
        return {"message": "Post deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting post: {e}")
        raise HTTPException(status_code=500, detail="Could not delete post")

# Comment routes
@router.post("/posts/{post_id}/comments", response_model=schemas.Comment, status_code=201, tags=["comments"])
async def create_comment(
    post_id: int,
    comment: schemas.CommentCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Add a comment to a post"""
    # Check if post exists
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    try:
        db_comment = models.Comment(
            **comment.dict(),
            post_id=post_id,
            author_id=current_user.id
        )
        db.add(db_comment)
        db.commit()
        db.refresh(db_comment)
        return db_comment
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating comment: {e}")
        raise HTTPException(status_code=500, detail="Could not create comment")

@router.put("/posts/{post_id}/comments/{comment_id}", response_model=schemas.Comment)
async def update_comment(
    post_id: int,
    comment_id: int,
    comment_update: schemas.CommentUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Update a comment. Only the comment author or admin can edit it."""
    # Check if post exists
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get the comment
    comment = db.query(models.Comment).filter(
        models.Comment.id == comment_id,
        models.Comment.post_id == post_id
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check authorization
    if not check_resource_permission(current_user, comment.author_id, "edit"):
        raise NotAuthorizedError("edit")

    try:
        # Update comment
        for field, value in comment_update.dict(exclude_unset=True).items():
            setattr(comment, field, value)
        db.commit()
        db.refresh(comment)
        return comment
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating comment: {e}")
        raise HTTPException(status_code=500, detail="Could not update comment")

@router.delete("/posts/{post_id}/comments/{comment_id}", status_code=200)
async def delete_comment(
    post_id: int,
    comment_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Delete a comment. Only the comment author or admin can delete it."""
    # Check if post exists
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get the comment
    comment = db.query(models.Comment).filter(
        models.Comment.id == comment_id,
        models.Comment.post_id == post_id
    ).first()
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Check authorization using the new helper
    if not check_resource_permission(current_user, comment.author_id, "delete"):
        raise NotAuthorizedError("delete")

    try:
        db.delete(comment)
        db.commit()
        return {"message": "Comment deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting comment: {e}")
        raise HTTPException(status_code=500, detail="Could not delete comment")

# Like routes
@router.post("/posts/{post_id}/like", status_code=201, tags=["likes"])
async def like_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Like a specific post"""
    # Check if post exists
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check if already liked
    existing_like = db.query(models.Like).filter(
        models.Like.post_id == post_id,
        models.Like.user_id == current_user.id
    ).first()
    if existing_like:
        raise HTTPException(status_code=409, detail="Post already liked")

    try:
        like = models.Like(post_id=post_id, user_id=current_user.id)
        db.add(like)
        db.commit()
        return {"message": "Post liked successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error liking post: {e}")
        raise HTTPException(status_code=500, detail="Could not like post")

@router.delete("/posts/{post_id}/like", status_code=200, tags=["likes"])
async def unlike_post(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Remove like from a post"""
    like = db.query(models.Like).filter(
        models.Like.post_id == post_id,
        models.Like.user_id == current_user.id
    ).first()
    if not like:
        raise HTTPException(status_code=404, detail="Post not liked")

    try:
        db.delete(like)
        db.commit()
        return {"message": "Post unliked successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error unliking post: {e}")
        raise HTTPException(status_code=500, detail="Could not unlike post")

# Tag routes
@router.post("/tags", response_model=schemas.Tag, status_code=201, tags=["tags"])
async def create_tag(
    tag: schemas.TagBase,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new tag"""
    if db.query(models.Tag).filter(models.Tag.name == tag.name).first():
        raise HTTPException(status_code=409, detail="Tag already exists")

    try:
        db_tag = models.Tag(**tag.dict())
        db.add(db_tag)
        db.commit()
        db.refresh(db_tag)
        return db_tag
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating tag: {e}")
        raise HTTPException(status_code=500, detail="Could not create tag")

@router.get("/tags/{tag_id}/posts", 
                response_model=schemas.PaginatedResponse[schemas.Post], 
                tags=["tags"])
async def get_posts_by_tag(
    tag_id: int,
    page: int = Query(1, gt=0),
    limit: int = Query(10, gt=0, le=100),
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional)
):
    """Get all posts with a specific tag"""
    # Check if tag exists
    tag = db.query(models.Tag).filter(models.Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    # Build query
    query = db.query(models.Post).join(models.post_tags).filter(models.post_tags.c.tag_id == tag_id)

    # Apply status filter if explicitly requested
    if status:
        if not current_user or (current_user.role not in ["admin", "author"]):
            raise HTTPException(status_code=403, detail="Not authorized to filter by status")
        query = query.join(models.Status).filter(models.Status.name == status)
    else:
        # Apply visibility rules
        query = filter_published_posts(query, current_user)

    # Get paginated results
    total = query.count()
    posts = query.offset((page - 1) * limit).limit(limit).all()

    return {
        "total": total,
        "pages": (total + limit - 1) // limit,
        "current_page": page,
        "items": posts
    }

# Add this helper function at the top with other helpers
def check_resource_permission(user: models.User, resource_owner_id: int, action: str) -> bool:
    """
    Check if user has permission to perform action on a resource.
    Actions: "edit", "delete"
    """
    # Admins can do anything
    if user.role == "admin":
        return True
    
    # Users can only modify their own resources
    return user.id == resource_owner_id

# Add this custom exception
class NotAuthorizedError(HTTPException):
    def __init__(self, action: str):
        super().__init__(
            status_code=403,
            detail=f"Not authorized to {action} this resource"
        )

# Add this with post routes to get post with like status
@router.get("/posts/{post_id}/with-like", response_model=schemas.PostWithLikeStatus)
async def get_post_with_like_status(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[models.User] = Depends(get_current_user_optional)
):
    """Get post by ID with like status for the current user"""
    post = db.query(models.Post).filter(models.Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Check if the user has liked this post
    is_liked = False
    if current_user:
        like = db.query(models.Like).filter(
            models.Like.post_id == post_id,
            models.Like.user_id == current_user.id
        ).first()
        is_liked = like is not None

    # Get like count
    likes_count = db.query(models.Like).filter(models.Like.post_id == post_id).count()

    return {
        **schemas.Post.from_orm(post).dict(),
        "is_liked": is_liked,
        "likes_count": likes_count
    }

@router.post("/status", response_model=schemas.Status, status_code=201, tags=["system"])
async def create_status(
    status: schemas.StatusCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Create a new status"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    db_status = models.Status(**status.model_dump())
    db.add(db_status)
    db.commit()
    db.refresh(db_status)
    return db_status

def validate_password(password: str) -> bool:
    """Validate password meets requirements"""
    if len(password) < 8:
        return False
    if not any(c.isupper() for c in password):
        return False
    if not any(c.islower() for c in password):
        return False
    if not any(c.isdigit() for c in password):
        return False
    return True

# Add auth routes to the router
@router.post("/auth/register", response_model=schemas.User, status_code=201, tags=["auth"])
async def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if username exists
    if db.query(models.User).filter(models.User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Check if email exists
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Validate password
    if not validate_password(user.password):
        raise HTTPException(
            status_code=422,
            detail="Password must be at least 8 characters and contain uppercase, lowercase, and numbers"
        )
    
    try:
        # Create user with proper role
        db_user = models.User(
            username=user.username,
            email=user.email,
            password=get_password_hash(user.password),
            role=user.role or "reader"  # Use provided role or default to reader
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except Exception as e:
        db.rollback()
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail="Could not register user")

@router.post("/auth/login", response_model=schemas.Token, tags=["auth"])
async def login(
    credentials: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    """Login user and return access token"""
    user = db.query(models.User).filter(models.User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user.username})
    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user
    )
