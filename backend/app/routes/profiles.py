from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from app.database import get_supabase_client

router = APIRouter()


class UserProfile(BaseModel):
    """Real user profile from Supabase."""
    id: str
    user_type: str  # "farmer" or "buyer"
    name: str
    phone: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    state: Optional[str] = None
    district: Optional[str] = None


class ProfileUpdate(BaseModel):
    """Profile update request."""
    name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    state: Optional[str] = None
    district: Optional[str] = None


@router.get("/me", response_model=UserProfile)
async def get_user_profile(
    user_id: str = Query(..., description="Supabase user ID"),
    supabase=Depends(get_supabase_client)
):
    """Get user's real profile from Supabase."""
    try:
        response = supabase.table("profiles").select("*").eq("id", user_id).execute()
        
        if not response.data:
            raise HTTPException(status_code=404, detail="Profile not found")
        
        profile = response.data[0]
        return UserProfile(
            id=profile.get("id"),
            user_type=profile.get("user_type", "farmer"),
            name=profile.get("name"),
            phone=profile.get("phone"),
            latitude=profile.get("latitude"),
            longitude=profile.get("longitude"),
            state=profile.get("state"),
            district=profile.get("district")
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/me")
async def update_profile(
    user_id: str = Query(..., description="Supabase user ID"),
    update: ProfileUpdate = None,
    supabase=Depends(get_supabase_client)
):
    """Update user's profile in Supabase."""
    try:
        data = {k: v for k, v in update.dict().items() if v is not None}
        
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")
        
        response = supabase.table("profiles").update(data).eq("id", user_id).execute()
        
        if response.data:
            return {"message": "Profile updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Update failed")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/farmers")
async def list_farmers(
    state: Optional[str] = Query(None),
    district: Optional[str] = Query(None),
    supabase=Depends(get_supabase_client)
):
    """List real farmers from Supabase."""
    try:
        query = supabase.table("profiles").select("*").eq("user_type", "farmer")
        
        if state:
            query = query.eq("state", state)
        if district:
            query = query.eq("district", district)
        
        response = query.limit(100).execute()
        
        return response.data if response.data else {"status": "UNAVAILABLE_DATA"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/buyers")
async def list_buyers(
    state: Optional[str] = Query(None),
    supabase=Depends(get_supabase_client)
):
    """List real buyers from Supabase."""
    try:
        query = supabase.table("profiles").select("*").eq("user_type", "buyer")
        
        if state:
            query = query.eq("state", state)
        
        response = query.limit(100).execute()
        
        return response.data if response.data else {"status": "UNAVAILABLE_DATA"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
