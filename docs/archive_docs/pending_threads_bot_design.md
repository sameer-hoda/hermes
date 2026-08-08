# Pending Threads Summary Bot - Design Document

## Overview
The Pending Threads Summary Bot is designed to analyze WhatsApp messages from both group and individual chats and provide a concise summary of pending items that require follow-up. The bot acts as a "chief of staff" that monitors all non-archived chats and provides a TL;DR of each pending item along with information about who it's pending with.

## Key Features
1. **Message Analysis**: Fetches messages from all active WhatsApp chats (both groups and individuals, non-archived)
2. **Pending Item Identification**: Uses AI to identify pending tasks and items requiring follow-up
3. **Batching**: Takes advantage of Gemini Pro 2.5's large context window to batch process messages from multiple chats
4. **Summary Generation**: Creates a concise summary of pending items with clear ownership
5. **72-Hour Window**: Focuses on conversations that happened in the last 72 hours
6. **Archived Chat Exclusion**: Automatically excludes archived chats from analysis
7. **Message Sending**: Can send messages through the Flask API to the WhatsApp client

## Architecture

### Components

1. **Message Fetcher**
   - Reads from `messages.db` and `whatsapp.db` SQLite databases
   - Retrieves messages from the last 72 hours
   - Resolves sender JIDs to display names using the contact resolution algorithm from the project manual

2. **Chat Processor**
   - Organizes messages by chat (both groups and individuals)
   - Filters out archived conversations using the `whatsmeow_chat_settings` table
   - Prepares data for AI analysis

3. **AI Analyzer**
   - Uses Gemini Pro 2.5 for analysis
   - Batches messages from multiple chats to maximize context window
   - Identifies pending items and their owners
   - Determines if items are pending on the user or others

4. **Summary Generator**
   - Formats the AI output into a readable summary
   - Organizes items by chat
   - Highlights critical items

5. **Output Handler**
   - Provides summaries in different formats (console, file, WhatsApp message)

### Data Flow

1. **Initialization**
   - Load database connections
   - Configure AI model (Gemini Pro 2.5)

2. **Chat Discovery**
   - Query all non-archived chats (both groups and individuals) with recent activity
   - Use the `whatsmeow_chat_settings` table to filter out archived chats

3. **Message Retrieval**
   - For each chat, query messages from the last 72 hours
   - Join with contact information to resolve sender names
   - Apply archived chat filtering

4. **Batching**
   - Group messages from multiple chats into batches that fit within the model's context window
   - Ensure related messages stay together when possible

5. **AI Analysis**
   - Send batches to Gemini Pro 2.5
   - Extract pending items with ownership information
   - Identify items pending on the user vs. others

6. **Summary Generation**
   - Consolidate AI results
   - Format into readable summaries
   - Organize by chat and priority

7. **Output**
   - Display in console
   - Optionally save to file
   - Optionally send to WhatsApp

## Database Schema Integration

### Key Tables Used
1. `messages` (from `messages.db`) - Contains message content and metadata
2. `chats` (from `messages.db`) - Contains chat metadata including last message time
3. `whatsmeow_message_secrets` (from `whatsapp.db`) - Maps message IDs to actual sender JIDs
4. `whatsmeow_contacts` (from `whatsapp.db`) - Contains contact name resolution information

### Contact Resolution Process
As per the project manual, the `sender` field in the `messages` table contains the group JID, not the individual sender's JID. To resolve the actual sender:
1. Join `messages.id` with `whatsmeow_message_secrets.message_id`
2. Use `whatsmeow_message_secrets.sender_jid` to look up the sender's name in `whatsmeow_contacts`

## AI Prompt Design

The AI prompt is designed to:
1. Identify pending items that require follow-up
2. Determine the owner of each pending item (user vs. others)
3. Extract context and deadline information when available
4. Categorize items by urgency

### Prompt Structure
```
You are an expert AI assistant that identifies PENDING ITEMS from WhatsApp messages across multiple chats.

INPUT:
- Messages from multiple WhatsApp chats from the last 72 hours
- Each chat's messages are separated by "=== CHAT: ChatName ==="
- Each message is formatted as: "[TIMESTAMP] SENDER_NAME: MESSAGE_CONTENT"

TASK:
For each chat, identify all pending items that require follow-up:
1. What the pending item is
2. Who it is pending with (specific person/group)
3. Any context or deadline information
4. Whether it's pending on the user or others

OUTPUT FORMAT:
Return a JSON object in this exact format:
{
  "groups": {
    "ChatName1": {
      "pending_items": [
        {
          "item": "Description of the pending item",
          "pending_with": "Person or group the item is pending with",
          "is_pending_on_user": boolean,
          "context": "Any relevant context",
          "deadline": "Deadline if mentioned",
          "urgency": "high|medium|low"
        }
      ]
    },
    "ChatName2": {
      "pending_items": [
        {
          "item": "Description of the pending item",
          "pending_with": "Person or group the item is pending with",
          "is_pending_on_user": boolean,
          "context": "Any relevant context",
          "deadline": "Deadline if mentioned",
          "urgency": "high|medium|low"
        }
      ]
    }
  }
}
```

## Implementation Plan

1. **Chat Discovery Module**
   - Implement database connection and query logic
   - Add archived chat filtering using `whatsmeow_chat_settings`
   - Retrieve both group and individual chats

2. **Message Fetching Module**
   - Implement database connection and query logic
   - Add contact resolution functionality
   - Filter messages from last 72 hours

3. **Batching Logic**
   - Create algorithm to batch messages within token limits
   - Ensure related messages stay together

4. **AI Integration**
   - Set up Gemini Pro 2.5 API integration
   - Implement prompt engineering
   - Handle API responses and error cases

5. **Summary Generation**
   - Create formatting functions
   - Implement grouping by chat
   - Add priority highlighting

6. **Output Handlers**
   - Console output
   - File export
   - WhatsApp integration

7. **Message Sending**
   - Implement API integration with Flask application
   - Add test message functionality
   - Include error handling and validation

## Error Handling

1. **Database Errors**
   - Handle missing or corrupted database files
   - Gracefully handle query failures

2. **AI API Errors**
   - Handle rate limiting
   - Manage API failures with retries
   - Handle parsing errors for AI responses

3. **General Errors**
   - Log errors with appropriate context
   - Continue processing when possible
   - Provide meaningful error messages to users

## Performance Considerations

1. **Database Queries**
   - Use appropriate indexes for faster lookups
   - Limit query results to necessary time window

2. **Batching**
   - Optimize batch sizes for AI model context window
   - Minimize number of API calls

3. **Memory Usage**
   - Process messages in chunks to manage memory
   - Clean up temporary data structures

## Testing Strategy

1. **Unit Tests**
   - Test message fetching and contact resolution
   - Test batching logic
   - Test AI response parsing

2. **Integration Tests**
   - Test end-to-end flow with sample data
   - Test different output formats

3. **Manual Testing**
   - Verify summaries with actual WhatsApp data
   - Check accuracy of pending item identification

## Message Sending Functionality

### Overview
The bot has been enhanced with the ability to send messages through the Flask API to the WhatsApp client. This functionality allows the bot to not only analyze pending items but also communicate results directly to users.

### Implementation Details

#### send_message_via_api()
This method sends a message through the Flask application's API endpoint:
- Connects to `http://localhost:5000/api/send_message`
- Sends a POST request with JSON payload containing user_id, recipient, and message
- Handles success and error responses appropriately

#### send_test_message()
This convenience method sends a predefined test message to verify the integration is working:
- Uses a default message content for testing
- Allows customization of recipient name and phone number
- Returns a boolean indicating success or failure

### Usage Examples
```python
# Send a test message
bot.send_test_message()

# Send a custom message
bot.send_message_via_api("917892083556", "Custom message content")

# Send a message as a different user
bot.send_message_via_api("917892083556", "Message from user2", "user2")

# Send the pending threads summary to Sameer Hoda
chats = bot.get_recent_groups()
batch_data = []
for chat in chats:
    messages = bot.get_group_messages_with_contacts(chat['jid'])
    messages_text = bot.format_messages_for_ai(messages)
    batch_data.append({
        "group_name": chat['name'],
        "messages_text": messages_text
    })
batch_results = bot.extract_pending_items_batch_with_gemini(batch_data)
whatsapp_summary = bot.format_summary_for_whatsapp(batch_results)
bot.send_message_via_api("917892083556", whatsapp_summary)
```

### Error Handling
The implementation includes comprehensive error handling for:
1. Network connectivity issues
2. API endpoint failures
3. Invalid response formats
4. Exception handling for unexpected errors

## Testing Strategy

1. **Unit Tests**
   - Test message fetching and contact resolution
   - Test batching logic
   - Test AI response parsing

2. **Integration Tests**
   - Test end-to-end flow with sample data
   - Test different output formats

3. **Manual Testing**
   - Verify summaries with actual WhatsApp data
   - Check accuracy of pending item identification
   - Test message sending functionality with actual WhatsApp client