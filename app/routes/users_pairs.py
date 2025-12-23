"""
User and Pair Management API Endpoints
Handles user authentication, profiles, and patient-caretaker pairing
"""

import logging
import uuid
from fastapi import APIRouter, HTTPException, status
from typing import Optional

from app.models.database_models import (
    UserCreate,
    UserProfile,
    PairCreate,
    PairInfo,
    PairConnection,
    SuccessResponse
)
from app.services.supabase_client import get_supabase_client

logger = logging.getLogger("UsersPairsAPI")
router = APIRouter(prefix="/api/v1", tags=["Users & Pairs"])

# ===== USER ENDPOINTS =====

@router.post("/users/signup", response_model=UserProfile, status_code=status.HTTP_201_CREATED)
async def signup_user(user: UserCreate):
    """
    Register a new user

    - **email**: User email
    - **password**: User password
    - **role**: User role (patient or caretaker)
    """
    try:
        logger.info(f"Creating new user: {user.email} with role: {user.role}")

        supabase = get_supabase_client()

        # Sign up user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": user.email,
            "password": user.password
        })

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user"
            )

        user_id = auth_response.user.id

        # Create pair if user is a patient
        pair_id = None
        if user.role == "patient":
            pair_result = supabase.table("pairs").insert({
                "patient_user_id": user_id,
                "caretaker_user_id": None
            }).execute()

            if pair_result.data and len(pair_result.data) > 0:
                pair_id = pair_result.data[0]["id"]
                logger.info(f"Created pair {pair_id} for patient {user_id}")

        logger.info(f"User {user_id} created successfully")

        return UserProfile(
            id=user_id,
            email=user.email,
            role=user.role,
            pair_id=pair_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )

@router.post("/users/login", response_model=UserProfile)
async def login_user(email: str, password: str):
    """
    Login user

    - **email**: User email
    - **password**: User password
    """
    try:
        logger.info(f"Login attempt for user: {email}")

        supabase = get_supabase_client()

        # Sign in user
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )

        user_id = auth_response.user.id

        # Get user's pair_id
        pair_id = None
        role = "caretaker"  # Default

        # Check if patient
        patient_pair = supabase.table("pairs") \
            .select("id") \
            .eq("patient_user_id", user_id) \
            .execute()

        if patient_pair.data and len(patient_pair.data) > 0:
            pair_id = patient_pair.data[0]["id"]
            role = "patient"
        else:
            # Check if caretaker
            caretaker_pair = supabase.table("pairs") \
                .select("id") \
                .eq("caretaker_user_id", user_id) \
                .execute()

            if caretaker_pair.data and len(caretaker_pair.data) > 0:
                pair_id = caretaker_pair.data[0]["id"]

        logger.info(f"User {user_id} logged in successfully")

        return UserProfile(
            id=user_id,
            email=email,
            role=role,
            pair_id=pair_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error logging in: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to login: {str(e)}"
        )

@router.get("/users/{user_id}", response_model=UserProfile)
async def get_user_profile(user_id: str):
    """
    Get user profile

    - **user_id**: User ID
    """
    try:
        logger.info(f"Fetching profile for user {user_id}")

        supabase = get_supabase_client()

        # Get user from Supabase Auth
        auth_user = supabase.auth.get_user()

        if not auth_user or auth_user.user.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get pair info
        pair_id = None
        role = "caretaker"

        patient_pair = supabase.table("pairs") \
            .select("id") \
            .eq("patient_user_id", user_id) \
            .execute()

        if patient_pair.data and len(patient_pair.data) > 0:
            pair_id = patient_pair.data[0]["id"]
            role = "patient"
        else:
            caretaker_pair = supabase.table("pairs") \
                .select("id") \
                .eq("caretaker_user_id", user_id) \
                .execute()

            if caretaker_pair.data and len(caretaker_pair.data) > 0:
                pair_id = caretaker_pair.data[0]["id"]

        return UserProfile(
            id=user_id,
            email=auth_user.user.email,
            role=role,
            pair_id=pair_id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user profile: {str(e)}"
        )

# ===== PAIR ENDPOINTS =====

@router.get("/pairs/{pair_id}", response_model=PairInfo)
async def get_pair_info(pair_id: str):
    """
    Get pair information

    - **pair_id**: Pair ID
    """
    try:
        logger.info(f"Fetching pair info for {pair_id}")

        supabase = get_supabase_client()

        result = supabase.table("pairs") \
            .select("*") \
            .eq("id", pair_id) \
            .execute()

        if not result.data or len(result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pair {pair_id} not found"
            )

        return PairInfo(**result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pair info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pair info: {str(e)}"
        )

@router.post("/pairs/connect", response_model=PairInfo)
async def connect_caretaker_to_patient(connection: PairConnection):
    """
    Connect a caretaker to a patient using pair code

    - **pair_code**: Patient's pair ID
    - **caretaker_user_id**: Caretaker's user ID
    """
    try:
        logger.info(f"Connecting caretaker {connection.caretaker_user_id} to pair {connection.pair_code}")

        supabase = get_supabase_client()

        # Check if pair exists
        pair_result = supabase.table("pairs") \
            .select("*") \
            .eq("id", connection.pair_code) \
            .execute()

        if not pair_result.data or len(pair_result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invalid pair code"
            )

        pair = pair_result.data[0]

        # Check if pair already has a caretaker
        if pair.get("caretaker_user_id"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This patient already has a caretaker"
            )

        # Update pair with caretaker
        update_result = supabase.table("pairs") \
            .update({"caretaker_user_id": connection.caretaker_user_id}) \
            .eq("id", connection.pair_code) \
            .execute()

        if not update_result.data or len(update_result.data) == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to connect caretaker"
            )

        logger.info(f"Caretaker {connection.caretaker_user_id} connected successfully")

        return PairInfo(**update_result.data[0])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error connecting caretaker: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to connect caretaker: {str(e)}"
        )
