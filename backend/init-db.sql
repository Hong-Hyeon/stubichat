-- Initialize Stubichat Database
-- This script creates the required tables for the NextAuth.js frontend

-- Create User table
CREATE TABLE IF NOT EXISTS "User" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "email" varchar(64) NOT NULL UNIQUE,
    "password" varchar(64)
);

-- Create Chat table
CREATE TABLE IF NOT EXISTS "Chat" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "createdAt" timestamp NOT NULL DEFAULT NOW(),
    "title" text NOT NULL,
    "userId" uuid NOT NULL REFERENCES "User"("id") ON DELETE CASCADE,
    "visibility" varchar(10) NOT NULL DEFAULT 'private' CHECK ("visibility" IN ('public', 'private'))
);

-- Create Message_v2 table (current version)
CREATE TABLE IF NOT EXISTS "Message_v2" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "chatId" uuid NOT NULL REFERENCES "Chat"("id") ON DELETE CASCADE,
    "role" varchar NOT NULL,
    "parts" json NOT NULL,
    "attachments" json NOT NULL DEFAULT '[]',
    "createdAt" timestamp NOT NULL DEFAULT NOW()
);

-- Create Vote_v2 table (current version)
CREATE TABLE IF NOT EXISTS "Vote_v2" (
    "chatId" uuid NOT NULL REFERENCES "Chat"("id") ON DELETE CASCADE,
    "messageId" uuid NOT NULL REFERENCES "Message_v2"("id") ON DELETE CASCADE,
    "isUpvoted" boolean NOT NULL,
    PRIMARY KEY ("chatId", "messageId")
);

-- Create Document table
CREATE TABLE IF NOT EXISTS "Document" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "title" text NOT NULL,
    "kind" varchar NOT NULL,
    "content" text NOT NULL,
    "userId" uuid NOT NULL REFERENCES "User"("id") ON DELETE CASCADE,
    "createdAt" timestamp NOT NULL DEFAULT NOW()
);

-- Create Suggestion table
CREATE TABLE IF NOT EXISTS "Suggestion" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "documentId" uuid NOT NULL REFERENCES "Document"("id") ON DELETE CASCADE,
    "content" text NOT NULL,
    "createdAt" timestamp NOT NULL DEFAULT NOW()
);

-- Create Stream table
CREATE TABLE IF NOT EXISTS "Stream" (
    "id" uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    "streamId" text NOT NULL UNIQUE,
    "chatId" uuid NOT NULL REFERENCES "Chat"("id") ON DELETE CASCADE,
    "createdAt" timestamp NOT NULL DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS "idx_user_email" ON "User"("email");
CREATE INDEX IF NOT EXISTS "idx_chat_userid" ON "Chat"("userId");
CREATE INDEX IF NOT EXISTS "idx_message_chatid" ON "Message_v2"("chatId");
CREATE INDEX IF NOT EXISTS "idx_vote_chatid" ON "Vote_v2"("chatId");
CREATE INDEX IF NOT EXISTS "idx_document_userid" ON "Document"("userId");
CREATE INDEX IF NOT EXISTS "idx_suggestion_documentid" ON "Suggestion"("documentId");
CREATE INDEX IF NOT EXISTS "idx_stream_chatid" ON "Stream"("chatId");

-- Insert a test guest user (optional)
INSERT INTO "User" ("email", "password") 
VALUES ('guest-test@example.com', 'dummy-password')
ON CONFLICT ("email") DO NOTHING; 