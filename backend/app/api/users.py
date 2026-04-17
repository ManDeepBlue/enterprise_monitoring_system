"""
API endpoints for user management.
Provides CRUD operations for system users, including role management and password updates.
Only accessible by users with the 'admin' role.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..deps import get_db, require_role
from ..db import models
from ..schemas.users import UserCreate, UserUpdate, UserOut
from ..schemas.common import Msg
from ..security import hash_password
from ..audit import log as audit_log

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """
    Retrieve a list of all registered users.
    """
    users = db.query(models.User).all()
    return users

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """
    Create a new system user.
    
    Validates that the role is valid and the email is unique.
    Hashes the password before storage.
    """
    # Validate the assigned role
    if payload.role not in ["admin", "analyst", "readonly"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    
    # Check for duplicate email
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
    # Create the user record
    new_user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Audit log the creation
    audit_log(db, current_user.email, "create_user", "user", new_user.email, meta={"role": payload.role})
    db.commit()
    return new_user

@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """
    Update an existing user's details.
    
    Handles email changes (with uniqueness check), role changes, 
    activation status, and password resets.
    Includes safeguards to prevent removing or deactivating the last active admin.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    # Handle email update
    if payload.email is not None:
        if payload.email != user.email:
            existing = db.query(models.User).filter(models.User.email == payload.email).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        user.email = payload.email
    
    # Handle role update
    if payload.role is not None:
        if payload.role not in ["admin", "analyst", "readonly"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
        
        # Guard: Prevent removing the last admin role
        if user.role == "admin" and payload.role != "admin":
            admin_count = db.query(models.User).filter(models.User.role == "admin", models.User.is_active == True).count()
            if admin_count <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the last active admin")
        user.role = payload.role
        
    # Handle activation status update
    if payload.is_active is not None:
        # Guard: Prevent deactivating the last active admin
        if user.role == "admin" and payload.is_active is False:
            admin_count = db.query(models.User).filter(models.User.role == "admin", models.User.is_active == True).count()
            if admin_count <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate the last active admin")
        user.is_active = payload.is_active
        
    # Handle password update
    if payload.password is not None and payload.password.strip():
        user.hashed_password = hash_password(payload.password)
        
    db.commit()
    db.refresh(user)
    
    # Audit log the update
    audit_log(db, current_user.email, "update_user", "user", user.email, meta={"role": user.role, "active": user.is_active})
    db.commit()
    return user

@router.delete("/{user_id}", response_model=Msg)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    """
    Permanently delete a user from the system.
    
    Includes safeguards to prevent deleting the last admin.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    # Guard: Prevent deleting the last admin
    if user.role == "admin":
        admin_count = db.query(models.User).filter(models.User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the last admin")
            
    db.delete(user)
    
    # Audit log the deletion
    audit_log(db, current_user.email, "delete_user", "user", user.email)
    db.commit()
    
    return Msg(message="User deleted successfully")
