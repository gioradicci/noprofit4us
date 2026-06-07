from fastapi import APIRouter, Depends, HTTPException
from dependencies.auth import get_current_user

router = APIRouter()

@router.get("/")
def get_members(user=Depends(get_current_user)):
    if user.role not in ["ADMIN", "TREASURER"]:
        raise HTTPException(403, "Forbidden")
    
    #TODO add list of members
    return []