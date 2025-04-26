import pandas as pd
from supabase_client import supabase
import io
from datetime import datetime

def upload_file_to_supabase(file, file_type: str, file_name: str = None):
    """
    Upload a file to Supabase storage and store its metadata
    """
    try:
        # Generate a unique file name if not provided
        if file_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"{file_type}_{timestamp}.csv"
        
        # Create the file path in Supabase storage
        file_path = f"raw-files/{file_type}/{file_name}"
        
        # Upload the file to Supabase storage
        supabase.storage.from_("raw-files").upload(
            file_path,
            file.getvalue(),
            {"content-type": "text/csv"}
        )
        
        # Store file metadata in the database
        supabase.table("file_metadata").insert({
            "file_name": file_name,
            "file_path": file_path,
            "file_type": file_type,
            "upload_date": datetime.now().isoformat()
        }).execute()
        
        return True, file_name
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
        return False, None

def get_file_from_supabase(file_type: str, file_name: str = None):
    """
    Retrieve a file from Supabase storage
    """
    try:
        if file_name is None:
            # Get the most recent file of the specified type
            response = supabase.table("file_metadata")\
                .select("*")\
                .eq("file_type", file_type)\
                .order("upload_date", desc=True)\
                .limit(1)\
                .execute()
            
            if not response.data:
                return None
            
            file_name = response.data[0]["file_name"]
        
        file_path = f"raw-files/{file_type}/{file_name}"
        response = supabase.storage.from_("raw-files").download(file_path)
        
        if response:
            return pd.read_csv(io.BytesIO(response))
        return None
    except Exception as e:
        print(f"Error retrieving file: {str(e)}")
        return None

def list_available_files(file_type: str = None):
    """
    List all available files in Supabase storage
    """
    try:
        query = supabase.table("file_metadata").select("*")
        if file_type:
            query = query.eq("file_type", file_type)
        
        response = query.order("upload_date", desc=True).execute()
        return response.data
    except Exception as e:
        print(f"Error listing files: {str(e)}")
        return [] 