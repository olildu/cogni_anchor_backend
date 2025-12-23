"""
Supabase Client Configuration
Handles connection to Supabase for database and storage operations
"""

import os
import logging
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger("SupabaseClient")

# --- Supabase Configuration ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # For admin operations

# Initialize Supabase client
supabase_client: Client = None

def get_supabase_client(use_service_key: bool = False) -> Client:
    """
    Get Supabase client instance

    Args:
        use_service_key: If True, uses service key for admin operations

    Returns:
        Supabase client instance
    """
    global supabase_client

    if not SUPABASE_URL:
        logger.error("SUPABASE_URL not found in environment variables")
        raise ValueError("SUPABASE_URL is required")

    # Choose which key to use
    key = SUPABASE_SERVICE_KEY if use_service_key and SUPABASE_SERVICE_KEY else SUPABASE_ANON_KEY

    if not key:
        logger.error("No Supabase key found in environment variables")
        raise ValueError("SUPABASE_ANON_KEY or SUPABASE_SERVICE_KEY is required")

    if supabase_client is None:
        try:
            supabase_client = create_client(SUPABASE_URL, key)
            logger.info(f"Supabase client initialized with {'service' if use_service_key else 'anon'} key")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    return supabase_client

# Initialize on module load
try:
    supabase_client = get_supabase_client()
except Exception as e:
    logger.warning(f"Supabase client not initialized: {e}")
