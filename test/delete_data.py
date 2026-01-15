import os
import asyncio
from supabase import create_client, Client

# --- CONFIGURATION ---
# Go to Supabase Dashboard -> Settings -> API -> Project URL
SUPABASE_URL = "https://joayctkupytsedmpfyng.supabase.co"

# Go to Supabase Dashboard -> Settings -> API -> service_role (secret)
# WARNING: This key has full admin rights. Do not share it.
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpvYXljdGt1cHl0c2VkbXBmeW5nIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTUyNzYwMCwiZXhwIjoyMDgxMTAzNjAwfQ.uSPP2CxwK0ipd9qGbGieP7RiTzNUw-1D63FYPZfj4No"

# Initialize Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

async def wipe_storage():
    """Delete all files from the 'face-images' bucket."""
    print("🗑️  Cleaning Storage: face-images...")
    try:
        bucket_name = "face-images"
        # List all files
        files = supabase.storage.from_(bucket_name).list()
        
        if files:
            file_paths = [f['name'] for f in files]
            # Delete files
            supabase.storage.from_(bucket_name).remove(file_paths)
            print(f"   ✅ Deleted {len(file_paths)} files.")
        else:
            print("   ℹ️  Bucket is empty.")
    except Exception as e:
        print(f"   ❌ Error cleaning storage: {e}")

def wipe_database():
    """Delete all rows from tables. Order matters due to Foreign Keys."""
    print("🗑️  Cleaning Database Tables...")
    
    # List of tables to clear in order (Child -> Parent)
    tables = [
        "face_embeddings",   # Linked to people
        "people",            # Linked to pairs
        "reminders",         # Linked to pairs
        "emergency_alerts",  # Linked to pairs
        "live_location",     # Linked to pairs/users
        "patient_status",    # Linked to users
        "pairs",             # Linked to users
        "users"              # Public users table (linked to auth.users)
    ]

    for table in tables:
        try:
            # Delete all rows (neq check is a hack to select all rows)
            # Or usually .delete().neq("id", 0) works if id is int, 
            # for UUIDs or generic delete, we can use a condition that is always true or not null
            
            # Using a condition that is likely true for all rows to trigger bulk delete
            # Since we have admin rights, RLS won't block us.
            
            # Note: Supabase-py syntax for "delete all" can be tricky without a WHERE clause.
            # We will try to fetch IDs first, then delete.
            
            # Fetch IDs to delete (limit to high number)
            res = supabase.table(table).select("id").execute()
            ids = [row['id'] for row in res.data]
            
            if ids:
                supabase.table(table).delete().in_("id", ids).execute()
                print(f"   ✅ Cleared table: {table} ({len(ids)} rows)")
            else:
                # Some tables might use user_id as PK, handle that if 'id' doesn't exist
                if table == "patient_status" or table == "live_location":
                     # These usually have patient_user_id as key based on your code
                     # Let's try deleting where column is not null
                     pass # Handled generally below if ID exists
                
                if not ids and table in ["patient_status", "live_location"]:
                     # Try alternative delete strategy
                     res = supabase.table(table).select("*").execute()
                     if res.data:
                         # Just delete everything not matching a dummy value
                         supabase.table(table).delete().neq("pair_id", "dummy").execute()
                         print(f"   ✅ Cleared table: {table}")
                     else:
                         print(f"   ℹ️  Table {table} is already empty.")
                else:
                    print(f"   ℹ️  Table {table} is already empty.")

        except Exception as e:
            print(f"   ⚠️  Could not clear {table} (might be empty or schema differs): {e}")

def wipe_auth_users():
    """Delete all users from Supabase Auth."""
    print("🗑️  Cleaning Auth Users...")
    try:
        # List users (limit 1000)
        users = supabase.auth.admin.list_users()
        
        count = 0
        for user in users:
            supabase.auth.admin.delete_user(user.id)
            count += 1
            
        print(f"   ✅ Deleted {count} users from Authentication.")
    except Exception as e:
        print(f"   ❌ Error deleting auth users: {e}")

if __name__ == "__main__":
    print("--- STARTING CLEANUP ---")
    
    # 1. Clean Storage (Files)
    asyncio.run(wipe_storage())
    
    # 2. Clean Public Tables (Data)
    wipe_database()
    
    # 3. Clean Auth Users (Login)
    wipe_auth_users()
    
    print("--- CLEANUP COMPLETE ---")