import sys
from supabase import create_client
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

def confirm_user(email: str):
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY not found in .env")
        return

    supabase = create_client(url, key)
    
    # Use admin API to confirm user
    try:
        # First find the user by email
        users = supabase.auth.admin.list_users()
        target_user = next((u for u in users if u.email == email), None)
        
        if not target_user:
            print(f"User with email {email} not found.")
            return
            
        # Update user to be confirmed
        supabase.auth.admin.update_user_by_id(
            target_user.id,
            {"email_confirm": True}
        )
        print(f"Successfully confirmed user: {email}")
    except Exception as e:
        print(f"Error confirming user: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python confirm_user.py <email>")
    else:
        confirm_user(sys.argv[1])
