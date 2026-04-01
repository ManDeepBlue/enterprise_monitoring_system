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
    users = db.query(models.User).all()
    return users

@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    if payload.role not in ["admin", "analyst", "readonly"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
    
    existing = db.query(models.User).filter(models.User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        
    new_user = models.User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    audit_log(db, current_user.email, "create_user", "user", new_user.email, meta={"role": payload.role})
    db.commit()
    return new_user

@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    if payload.email is not None:
        if payload.email != user.email:
            existing = db.query(models.User).filter(models.User.email == payload.email).first()
            if existing:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
        user.email = payload.email
    
    if payload.role is not None:
        if payload.role not in ["admin", "analyst", "readonly"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
        # Prevent removing the last admin
        if user.role == "admin" and payload.role != "admin":
            admin_count = db.query(models.User).filter(models.User.role == "admin", models.User.is_active == True).count()
            if admin_count <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove the last active admin")
        user.role = payload.role
        
    if payload.is_active is not None:
        # Prevent deactivating the last admin
        if user.role == "admin" and payload.is_active is False:
            admin_count = db.query(models.User).filter(models.User.role == "admin", models.User.is_active == True).count()
            if admin_count <= 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate the last active admin")
        user.is_active = payload.is_active
        
    if payload.password is not None and payload.password.strip():
        user.hashed_password = hash_password(payload.password)
        
    db.commit()
    db.refresh(user)
    
    audit_log(db, current_user.email, "update_user", "user", user.email, meta={"role": user.role, "active": user.is_active})
    db.commit()
    return user

@router.delete("/{user_id}", response_model=Msg)
def delete_user(user_id: int, db: Session = Depends(get_db), current_user=Depends(require_role("admin"))):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    # Prevent deleting the last admin
    if user.role == "admin":
        admin_count = db.query(models.User).filter(models.User.role == "admin").count()
        if admin_count <= 1:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the last admin")
            
    db.delete(user)
    
    audit_log(db, current_user.email, "delete_user", "user", user.email)
    db.commit()
    
    return Msg(message="User deleted successfully")
