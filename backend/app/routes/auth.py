from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from app.database import get_supabase_client
from app.config import settings

router = APIRouter()


class SignUpRequest(BaseModel):
    """User signup request."""
    phone: str
    password: str


class SignUpResponse(BaseModel):
    """Signup response."""
    user_id: str
    message: str


class LoginRequest(BaseModel):
    """User login request."""
    phone: str
    password: str


class LoginResponse(BaseModel):
    """Login response."""
    access_token: str
    user_id: str
    user_type: str  # "farmer" or "buyer"


@router.post("/signup", response_model=SignUpResponse)
async def signup(
    request: SignUpRequest,
    supabase=Depends(get_supabase_client)
):
    """
    Register new user via Supabase Auth.
    
    - No pre-created accounts
    - Uses Supabase SMS OTP
    - User must set password securely
    """
    try:
        # Create user in Supabase Auth
        response = supabase.auth.sign_up({
            "phone": request.phone,
            "password": request.password
        })
        
        if response.user:
            return SignUpResponse(
                user_id=response.user.id,
                message="Signup successful. Please verify with OTP."
            )
        else:
            raise HTTPException(status_code=400, detail="Signup failed")
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    supabase=Depends(get_supabase_client)
):
    """
    Login user via Supabase Auth.
    
    - Real authentication
    - No demo credentials
    """
    try:
        response = supabase.auth.sign_in_with_password({
            "phone": request.phone,
            "password": request.password
        })
        
        if response.session:
            # Get user type from profiles table
            user_profile = supabase.table("profiles").select("user_type").eq(
                "id", response.user.id
            ).execute()
            
            user_type = "farmer"
            if user_profile.data:
                user_type = user_profile.data[0].get("user_type", "farmer")
            
            return LoginResponse(
                access_token=response.session.access_token,
                user_id=response.user.id,
                user_type=user_type
            )
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")


@router.post("/logout")
async def logout(supabase=Depends(get_supabase_client)):
    """Logout user."""
    try:
        supabase.auth.sign_out()
        return {"message": "Logout successful"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify-otp")
async def verify_otp(
    phone: str,
    otp: str,
    supabase=Depends(get_supabase_client)
):
    """
    Verify OTP for phone authentication.
    
    - Supabase SMS OTP verification
    - No hardcoded OTP codes
    """
    try:
        response = supabase.auth.verify_otp({
            "phone": phone,
            "token": otp,
            "type": "sms"
        })
        
        if response.session:
            return {
                "success": True,
                "access_token": response.session.access_token,
                "user_id": response.user.id
            }
        else:
            raise HTTPException(status_code=401, detail="Invalid OTP")
    
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/me")
async def get_current_user(
    token: str,
    supabase=Depends(get_supabase_client)
):
    """Get current authenticated user info."""
    try:
        user = supabase.auth.get_user(token)
        
        if user:
            return {
                "id": user.id,
                "phone": user.user_metadata.get("phone")
            }
        else:
            raise HTTPException(status_code=401, detail="Unauthorized")
    
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
