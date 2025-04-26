-- Create the file_metadata table
CREATE TABLE IF NOT EXISTS file_metadata (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_type TEXT NOT NULL,
    upload_date TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create an index on file_type and upload_date for faster queries
CREATE INDEX IF NOT EXISTS idx_file_metadata_type_date ON file_metadata(file_type, upload_date DESC);

-- Add RLS (Row Level Security) policies
ALTER TABLE file_metadata ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows all operations (you can modify this based on your security needs)
CREATE POLICY "Allow all operations" ON file_metadata
    FOR ALL
    USING (true)
    WITH CHECK (true); 