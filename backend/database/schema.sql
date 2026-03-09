-- Semantic Media Engine Database Schema
-- This schema defines the structure for storing media metadata

-- Create ENUM type for media_type
CREATE TYPE media_type_enum AS ENUM ('book', 'tv_show');

-- Create media_items table
CREATE TABLE IF NOT EXISTS media_items (
    id UUID PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    media_type media_type_enum NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_media_items_id ON media_items(id);
CREATE INDEX IF NOT EXISTS idx_media_items_media_type ON media_items(media_type);
CREATE INDEX IF NOT EXISTS idx_media_items_metadata ON media_items USING GIN(metadata);

-- Create index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS idx_media_items_created_at ON media_items(created_at);

-- Create function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at on row updates
CREATE TRIGGER update_media_items_updated_at
    BEFORE UPDATE ON media_items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE media_items IS 'Stores metadata for books and TV shows';
COMMENT ON COLUMN media_items.id IS 'Unique identifier (UUID v4)';
COMMENT ON COLUMN media_items.title IS 'Media title (max 500 characters)';
COMMENT ON COLUMN media_items.description IS 'Plot/synopsis description';
COMMENT ON COLUMN media_items.media_type IS 'Type of media: book or tv_show';
COMMENT ON COLUMN media_items.metadata IS 'Additional metadata stored as JSON (author, genre, year, rating, etc.)';
COMMENT ON COLUMN media_items.created_at IS 'Timestamp when record was created';
COMMENT ON COLUMN media_items.updated_at IS 'Timestamp when record was last updated';
