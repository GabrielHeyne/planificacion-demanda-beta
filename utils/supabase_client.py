from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY
import pandas as pd
import io
import base64

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def store_raw_file(file_name: str, file_content: bytes, file_type: str):
    """
    Store a raw file in Supabase Storage
    """
    try:
        # Create a unique path for the file
        file_path = f"raw-files/{file_name}"
        
        # Upload the file to Supabase Storage
        supabase.storage.from_("raw-files").upload(
            file_path,
            file_content,
            {"content-type": f"application/{file_type}"}
        )
        
        # Store file metadata in the database
        supabase.table("file_metadata").insert({
            "file_name": file_name,
            "file_path": file_path,
            "file_type": file_type,
            "upload_date": "now()"
        }).execute()
        
        return True
    except Exception as e:
        print(f"Error storing file: {str(e)}")
        return False

def store_processed_data(table_name: str, data: pd.DataFrame):
    """
    Store processed data in a Supabase table
    """
    try:
        # Convert DataFrame to list of dictionaries
        records = data.to_dict('records')
        
        # Insert data into the specified table
        supabase.table(table_name).insert(records).execute()
        return True
    except Exception as e:
        print(f"Error storing processed data: {str(e)}")
        return False

def get_raw_file(file_name: str):
    """
    Retrieve a raw file from Supabase Storage
    """
    try:
        file_path = f"raw-files/{file_name}"
        response = supabase.storage.from_("raw-files").download(file_path)
        return response
    except Exception as e:
        print(f"Error retrieving file: {str(e)}")
        return None

def get_processed_data(table_name: str):
    """
    Retrieve processed data from a Supabase table
    """
    try:
        response = supabase.table(table_name).select("*").execute()
        return pd.DataFrame(response.data)
    except Exception as e:
        print(f"Error retrieving processed data: {str(e)}")
        return None 