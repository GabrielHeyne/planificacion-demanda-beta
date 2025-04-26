import pandas as pd
import io
from file_operations import upload_file_to_supabase, get_file_from_supabase, list_available_files

def test_file_operations():
    print("Testing Supabase file operations...")
    
    # Create a test DataFrame
    test_data = {
        'sku': ['SKU001', 'SKU002', 'SKU003'],
        'fecha': ['2024-01-01', '2024-01-02', '2024-01-03'],
        'demanda': [100, 200, 300]
    }
    df = pd.DataFrame(test_data)
    
    # Convert DataFrame to CSV bytes
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    
    # Test 1: Upload file
    print("\nTest 1: Uploading file...")
    success, file_name = upload_file_to_supabase(csv_buffer, 'test')
    if success:
        print(f"✅ File uploaded successfully as: {file_name}")
    else:
        print("❌ File upload failed")
        return
    
    # Test 2: List files
    print("\nTest 2: Listing files...")
    files = list_available_files('test')
    if files:
        print("✅ Files listed successfully:")
        for file in files:
            print(f"  - {file['file_name']} ({file['upload_date']})")
    else:
        print("❌ No files found or error listing files")
    
    # Test 3: Retrieve file
    print("\nTest 3: Retrieving file...")
    retrieved_df = get_file_from_supabase('test', file_name)
    if retrieved_df is not None:
        print("✅ File retrieved successfully")
        print("\nRetrieved data:")
        print(retrieved_df)
    else:
        print("❌ File retrieval failed")

if __name__ == "__main__":
    test_file_operations() 