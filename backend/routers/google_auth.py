"""Google OAuth authentication"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from backend.db.database import get_db
from backend.core.models import User
from backend.utils.security import create_access_token
import os

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

class GoogleAuthRequest(BaseModel):
    credential: str  # JWT token from Google

@router.post("/google")
def google_auth(request: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Authenticate with Google OAuth"""
    
    try:
        # Verify the Google token
        idinfo = id_token.verify_oauth2_token(
            request.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        
        # Extract user info from Google
        email = idinfo.get('email')
        name = idinfo.get('name')
        google_id = idinfo.get('sub')  # Google's unique user ID
        
        if not email:
            raise HTTPException(status_code=400, detail="No email from Google")
        
        # Check if user exists
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            # Create new user
            username = email.split('@')[0]  # Use email prefix as username
            
            # Make username unique if already exists
            base_username = username
            counter = 1
            while db.query(User).filter(User.username == username).first():
                username = f"{base_username}{counter}"
                counter += 1
            
            user = User(
                username=username,
                email=email,
                full_name=name,
                hashed_password="",  # No password for OAuth users
                google_id=google_id
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        
        # Create JWT token for our app
        access_token = create_access_token(data={"sub": user.username})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name
            }
        }
        
    except ValueError as e:
        # Invalid token
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Google auth failed: {str(e)}")