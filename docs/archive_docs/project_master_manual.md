# WhatsApp Task God v1 - Project Master Manual

## Table of Contents
1. [Project Overview](#project-overview)
2. [Component Functions](#component-functions)
3. [User Tagging Detection](#user-tagging-detection)
4. [Database Structure Overview](#database-structure-overview)
5. [Core Database Schema](#core-database-schema)
6. [Key Cross-Database Relationships](#key-cross-database-relationships)
7. [Database Relationship Overview](#database-relationship-overview)
8. [Key Tables and Relationships](#key-tables-and-relationships)
9. [Critical Understanding](#critical-understanding)
10. [Contact Resolution Algorithm](#contact-resolution-algorithm)
11. [Name Resolution Priority](#name-resolution-priority)
12. [Python Implementation Examples](#python-implementation-examples)
13. [Common Pitfalls and Solutions](#common-pitfalls-and-solutions)
14. [Database Query Examples](#database-query-examples)
15. [Performance Considerations](#performance-considerations)
16. [Quick Reference](#quick-reference)
17. [Common Use Cases](#common-use-cases)
18. [Data Export Patterns](#data-export-patterns)
19. [Database Maintenance](#database-maintenance)
20. [Troubleshooting](#troubleshooting)
21. [Security Considerations](#security-considerations)
22. [Practical Database Insights](#practical-database-insights)
23. [Database Access Examples](#database-access-examples)
24. [Technical Glossary Integration](#technical-glossary-integration)

## Project Overview

This project consists of multiple components working together to analyze WhatsApp group messages, identify tasks and discussion threads, and provide AI-powered responses to queries. The system can detect when users are mentioned in messages and respond appropriately.

## Component Functions

### 1. analyze_group_tasks.py
Analyzes WhatsApp group messages to identify pending tasks and action items:
- Connects to SQLite databases (whatsapp.db and messages.db) to retrieve group messages
- Resolves contact names for better readability
- Uses Google's Gemini API to analyze messages and extract:
  - Pending tasks with owners (especially those with @mentions)
  - Task status and duration pending
  - Context and reply thread information
- Focuses on actionable items with clear assignments through @mentions

### 2. group_threads_summary_v2.py
Generates comprehensive summaries of group discussion threads:
- Analyzes messages from multiple WhatsApp groups
- Identifies key discussion threads and their progression
- Tracks thread status (ongoing, resolved, stalled, etc.)
- Extracts main tasks and their current status
- Analyzes 24-hour progress in groups
- Can send formatted summaries back to WhatsApp groups
- Includes scheduling functionality for daily summaries at 9 AM IST
- Handles timezone conversions between IST and UTC

### 3. app.py (Flask Application)
Web application that serves as an interface and API proxy:
- Provides a web UI for monitoring WhatsApp client status
- Handles Server-Sent Events (SSE) for real-time updates
- Proxies API calls to the Go WhatsApp client
- Implements an AI chatbot that responds to queries with context from chat history
- Handles media serving for downloaded WhatsApp media
- **Handles mention notifications** when users are tagged in messages

### 4. main.go (WhatsApp Client)
Core WhatsApp client implemented in Go:
- Connects to WhatsApp using the whatsmeow library
- Handles QR code authentication
- Stores messages and chats in SQLite databases
- Processes incoming messages and history sync events
- Provides REST APIs for sending messages and downloading media
- **Detects mentions in messages and notifies app.py**

## User Tagging Detection

Yes, the system detects when a user is tagged in a message:

1. **Detection in main.go**: The `handleMessage` function checks for mentions in extended text messages:
   ```go
   if extendedMsg := msg.Message.GetExtendedTextMessage(); extendedMsg != nil {
       if extendedMsg.ContextInfo != nil {
           mentionedJIDs := extendedMsg.ContextInfo.MentionedJID
           if len(mentionedJIDs) > 0 {
               // Process mentions
           }
       }
   }
   ```

2. **Bot-specific mention detection**: The system specifically identifies when only the bot itself was mentioned:
   ```go
   isOnlyBotMentioned := false
   if client.Store.ID != nil && len(mentionedJIDs) == 1 {
       botUser := client.Store.ID.User
       mentionedJIDString := mentionedJIDs[0]
       parsedJID, err := types.ParseJID(mentionedJIDString)
       if err == nil && parsedJID.User == botUser {
           isOnlyBotMentioned = true
       }
   }
   ```

3. **Notification to app.py**: When the bot is mentioned, the `notifyMention()` function sends a POST request to app.py:
   - Endpoint: `http://localhost:5000/api/mention_notification`
   - Payload includes: chat_jid, sender_jid, message, and mentioned_jids

4. **Processing in app.py**: The Flask application receives this notification at the `/api/mention_notification` endpoint and can trigger AI responses or other actions.

This system enables the bot to respond intelligently when mentioned in group conversations, providing context-aware responses based on the conversation history.

## Database Structure Overview

The WhatsApp bridge uses two SQLite databases:

1. **`whatsapp.db`** - Contains device configuration, cryptographic data, contacts, and session information
2. **`messages.db`** - Contains chat metadata and message content

This separation allows for better organization and performance, with configuration data separate from the potentially large message history.

## Core Database Schema

### Database 1: `whatsapp.db`

#### `whatsmeow_device`
The central table that stores device identity and cryptographic material.

| Field Name           | Type    | Description                                                  |
|----------------------|---------|--------------------------------------------------------------|
| jid                  | TEXT    | **Primary Key.** WhatsApp JID (Jabber ID) for the device.    |
| registration_id      | BIGINT  | Registration ID for the device (unsigned 32-bit integer).    |
| noise_key            | bytea   | 32-byte Noise protocol key for secure communication.         |
| identity_key         | bytea   | 32-byte identity key for the device.                         |
| signed_pre_key       | bytea   | 32-byte signed pre-key for session establishment.            |
| signed_pre_key_id    | INTEGER | ID of the signed pre-key (unsigned 24-bit integer).          |
| signed_pre_key_sig   | bytea   | 64-byte signature for the signed pre-key.                    |
| adv_key              | bytea   | Advertisement key for device identity.                       |
| adv_details          | bytea   | Advertisement details for device identity.                   |
| adv_account_sig      | bytea   | 64-byte account signature for device advertisement.          |
| adv_device_sig       | bytea   | 64-byte device signature for device advertisement.           |
| platform             | TEXT    | Device platform (e.g., Android, iOS, Web).                   |
| business_name        | TEXT    | Business name associated with the device (if any).           |
| push_name            | TEXT    | Push name (display name) for the device.                     |
| adv_account_sig_key  | bytea   | 32-byte key for account signature (optional).                |
| facebook_uuid        | uuid    | Facebook UUID associated with the device (optional).         |

**Purpose**: Stores the device identity and cryptographic material needed for WhatsApp's end-to-end encryption. This is the foundation of the WhatsApp connection.

#### `whatsmeow_contacts`
Stores contact information for WhatsApp users.

| Field Name    | Type  | Description                                        |
|---------------|-------|----------------------------------------------------|
| our_jid       | TEXT  | **Primary Key (1).** JID of our device (FK).       |
| their_jid     | TEXT  | **Primary Key (2).** JID of the contact.           |
| first_name    | TEXT  | First name of the contact.                         |
| full_name     | TEXT  | Full name of the contact.                          |
| push_name     | TEXT  | Push name (display name) of the contact.           |
| business_name | TEXT  | Business name of the contact (if any).             |

**Purpose**: Maintains a directory of all contacts, including their display names and identifiers. This table is crucial for resolving JIDs to human-readable names.

#### `whatsmeow_message_secrets`
Maps message IDs to actual sender JIDs, especially important for group chats.

| Field Name  | Type  | Description                                          |
|-------------|-------|------------------------------------------------------|
| our_jid     | TEXT  | **Primary Key (1).** JID of our device (FK).         |
| chat_jid    | TEXT  | **Primary Key (2).** JID of the chat.                |
| sender_jid  | TEXT  | **Primary Key (3).** JID of the sender.              |
| message_id  | TEXT  | **Primary Key (4).** ID of the message.              |
| key         | bytea | Secret key for the message.                          |

**Purpose**: Critical for resolving message senders in group chats. The `messages` table in `messages.db` stores the group JID as sender, while this table maps the message ID to the actual individual sender's JID.

### Database 2: `messages.db`

#### `chats`
Stores metadata about conversations.

| Field Name        | Type      | Description                                  |
|-------------------|-----------|----------------------------------------------|
| jid               | TEXT      | **Primary Key.** WhatsApp JID for the chat.  |
| name              | TEXT      | Display name of the chat.                    |
| last_message_time | TIMESTAMP | Timestamp of the last message in the chat.   |

**Purpose**: Maintains a list of all conversations (both individual and group) with their display names and last activity time.

#### `messages`
Stores the actual message content and metadata.

| Field Name      | Type      | Description                                    |
|-----------------|-----------|------------------------------------------------|
| id              | TEXT      | **Primary Key (1).** Message ID.               |
| chat_jid        | TEXT      | **Primary Key (2).** JID of the chat (FK).     |
| sender          | TEXT      | Sender identifier (group JID for group chats). |
| content         | TEXT      | Text content of the message.                   |
| timestamp       | TIMESTAMP | When the message was sent.                     |
| is_from_me      | BOOLEAN   | True if sent by the user, false if received.   |
| media_type      | TEXT      | Type of media (image, video, audio, document). |
| filename        | TEXT      | Filename for media messages.                   |
| url             | TEXT      | URL for media content.                         |
| media_key       | BLOB      | Key for decrypting media.                      |
| file_sha256     | BLOB      | SHA256 hash of the file.                       |
| file_enc_sha256 | BLOB      | SHA256 hash of the encrypted file.             |
| file_length     | INTEGER   | Size of the file in bytes.                     |

**Purpose**: Stores all message content, including text and metadata for media messages. For group messages, the `sender` field contains the group JID, not the individual sender's JID.

## Key Cross-Database Relationships

### 1. Message Sender Resolution in Groups

The most critical cross-database relationship is for resolving message senders in group chats:

```
messages.db:messages.id + messages.chat_jid
            ↓
whatsapp.db:whatsmeow_message_secrets.message_id + whatsmeow_message_secrets.chat_jid
            ↓
whatsmeow_message_secrets.sender_jid
            ↓
whatsmeow_contacts.their_jid → Contact name information
```

This relationship is necessary because in group chats, the `sender` field in the `messages` table contains the group JID, not the individual sender's JID. The actual sender must be resolved through the `whatsmeow_message_secrets` table.

### 2. Chat Name Resolution

For resolving chat names:

```
messages.db:chats.jid
            ↓
whatsapp.db:whatsmeow_contacts.their_jid → Contact name information
```

This relationship helps in displaying proper names for chats, especially when the name in the `chats` table is missing or just contains a phone number.

## Database Relationship Overview

The WhatsApp bridge uses a multi-table approach to link messages to contact information:

```
messages.sender → whatsmeow_message_secrets.sender_jid → whatsmeow_contacts.their_jid
```

## Key Tables and Relationships

### 1. `messages` Table (in `messages.db`)
- **`sender`**: Contains the group JID (e.g., `120363049581425328`) - NOT the individual sender's JID
- **`chat_jid`**: The group or chat JID (e.g., `120363049581425328@g.us`)
- **`id`**: Unique message ID
- **`content`**: Message text content

### 2. `whatsmeow_message_secrets` Table (in `whatsapp.db`)
- **`chat_jid`**: Group JID with `@g.us` suffix (e.g., `120363049581425328@g.us`)
- **`sender_jid`**: Individual sender's JID (e.g., `919833995903@s.whatsapp.net`)
- **`message_id`**: Links to `messages.id`
- **Purpose**: Maps group messages to individual senders

### 3. `whatsmeow_contacts` Table (in `whatsapp.db`)
- **`their_jid`**: Individual contact JID (e.g., `919833995903@s.whatsapp.net`)
- **`full_name`**: Complete contact name
- **`first_name`**: First name only
- **`push_name`**: Display name from WhatsApp
- **`business_name`**: Business name (if applicable)

## Critical Understanding

### The Sender Field Confusion
⚠️ **Important**: The `sender` field in the `messages` table does NOT contain the individual sender's JID. Instead, it contains the group JID without the `@g.us` suffix.

**Example from actual data:**
```sql
-- messages table
id: 3AA620E4B636B7BFC5BF
chat_jid: 120363049581425328@g.us
sender: 120363049581425328  -- This is the GROUP JID, not individual sender!

-- whatsmeow_message_secrets table
chat_jid: 120363049581425328@g.us
sender_jid: 919833995903@s.whatsapp.net  -- This is the ACTUAL sender
message_id: 3AA620E4B636B7BFC5BF

-- whatsmeow_contacts table
their_jid: 919833995903@s.whatsapp.net
full_name: (null)
push_name: Nikhil Saxena
```

## Contact Resolution Algorithm

### Step 1: Link Message to Actual Sender
```sql
SELECT 
    m.id,
    m.content,
    m.timestamp,
    ms.sender_jid as actual_sender
FROM messages m
JOIN whatsmeow_message_secrets ms ON (
    m.id = ms.message_id AND 
    m.chat_jid = ms.chat_jid
)
WHERE m.chat_jid = '120363049581425328@g.us';
```

### Step 2: Resolve Sender to Contact Name
```sql
SELECT 
    m.id,
    m.content,
    m.timestamp,
    ms.sender_jid,
    COALESCE(
        c.full_name,
        c.first_name,
        c.push_name,
        c.business_name,
        SUBSTR(ms.sender_jid, 1, INSTR(ms.sender_jid, '@') - 1)
    ) as sender_name
FROM messages m
JOIN whatsmeow_message_secrets ms ON (
    m.id = ms.message_id AND 
    m.chat_jid = ms.chat_jid
)
LEFT JOIN whatsmeow_contacts c ON ms.sender_jid = c.their_jid
WHERE m.chat_jid = '120363049581425328@g.us'
ORDER BY m.timestamp ASC;
```

## Name Resolution Priority

When resolving contact names, use this priority order:
1. **`full_name`** - Complete name (highest priority)
2. **`first_name`** - First name only
3. **`push_name`** - WhatsApp display name
4. **`business_name`** - Business account name
5. **Phone number** - Extracted from JID (fallback)

## Python Implementation Examples

### Complete Contact Resolution Function
```python
import sqlite3

def get_group_messages_with_contacts(group_jid, whatsapp_db_path, messages_db_path):
    """
    Get group messages with proper contact name resolution
    """
    whatsapp_conn = sqlite3.connect(whatsapp_db_path)
    messages_conn = sqlite3.connect(messages_db_path)
    
    query = """
    SELECT 
        m.id,
        m.content,
        m.timestamp,
        ms.sender_jid,
        COALESCE(
            c.full_name,
            c.first_name,
            c.push_name,
            c.business_name,
            SUBSTR(ms.sender_jid, 1, INSTR(ms.sender_jid, '@') - 1)
        ) as sender_name
    FROM messages m
    JOIN whatsmeow_message_secrets ms ON (
        m.id = ms.message_id AND 
        m.chat_jid = ms.chat_jid
    )
    LEFT JOIN whatsmeow_contacts c ON ms.sender_jid = c.their_jid
    WHERE m.chat_jid = ?
    ORDER BY m.timestamp ASC
    """
    
    # Execute query across both databases
    messages_conn.execute("ATTACH DATABASE ? AS whatsapp_db", (whatsapp_db_path,))
    
    results = messages_conn.execute(query.replace(
        "whatsmeow_message_secrets ms", 
        "whatsapp_db.whatsmeow_message_secrets ms"
    ).replace(
        "whatsmeow_contacts c",
        "whatsapp_db.whatsmeow_contacts c"
    ), (group_jid,)).fetchall()
    
    whatsapp_conn.close()
    messages_conn.close()
    
    return results

# Usage example
messages = get_group_messages_with_contacts(
    "120363049581425328@g.us",
    "store/whatsapp.db",
    "store/messages.db"
)

for msg_id, content, timestamp, sender_jid, sender_name in messages:
    print(f"[{timestamp}] {sender_name}: {content}")
```

### Simplified Contact Cache Approach
```python
def build_contact_cache(whatsapp_db_path):
    """Build a cache of JID to name mappings"""
    conn = sqlite3.connect(whatsapp_db_path)
    
    contacts = {}
    query = """
        SELECT their_jid, first_name, full_name, push_name, business_name
        FROM whatsmeow_contacts
    """
    
    for row in conn.execute(query):
        jid, first, full, push, business = row
        name = full or first or push or business or jid.split('@')[0]
        contacts[jid] = name
    
    conn.close()
    return contacts

def get_message_sender_mapping(messages_db_path, whatsapp_db_path, group_jid):
    """Get mapping of message IDs to sender JIDs"""
    whatsapp_conn = sqlite3.connect(whatsapp_db_path)
    
    query = """
        SELECT message_id, sender_jid
        FROM whatsmeow_message_secrets
        WHERE chat_jid = ?
    """
    
    sender_mapping = {}
    for msg_id, sender_jid in whatsapp_conn.execute(query, (group_jid,)):
        sender_mapping[msg_id] = sender_jid
    
    whatsapp_conn.close()
    return sender_mapping
```

## Common Pitfalls and Solutions

### ❌ Wrong Approach
```python
# This will NOT work - sender field is group JID, not individual
sender_name = contacts.get(message.sender)  # Wrong!
```

### ✅ Correct Approach
```python
# Get actual sender from message_secrets table
actual_sender = message_secrets_mapping.get(message.id)
sender_name = contacts.get(actual_sender)  # Correct!
```

## Database Query Examples

### Get All Senders in a Group
```sql
SELECT DISTINCT 
    ms.sender_jid,
    COALESCE(c.full_name, c.push_name, c.first_name) as name
FROM whatsmeow_message_secrets ms
LEFT JOIN whatsmeow_contacts c ON ms.sender_jid = c.their_jid
WHERE ms.chat_jid = '120363049581425328@g.us';
```

### Count Messages by Sender
```sql
SELECT 
    COALESCE(c.full_name, c.push_name, c.first_name, 
             SUBSTR(ms.sender_jid, 1, INSTR(ms.sender_jid, '@') - 1)) as sender_name,
    COUNT(*) as message_count
FROM messages m
JOIN whatsmeow_message_secrets ms ON m.id = ms.message_id
LEFT JOIN whatsmeow_contacts c ON ms.sender_jid = c.their_jid
WHERE m.chat_jid = '120363049581425328@g.us'
GROUP BY ms.sender_jid
ORDER BY message_count DESC;
```

### Recent Messages with Sender Names
```sql
SELECT 
    m.timestamp,
    COALESCE(c.push_name, c.full_name, 
             SUBSTR(ms.sender_jid, 1, INSTR(ms.sender_jid, '@') - 1)) as sender,
    m.content
FROM messages m
JOIN whatsmeow_message_secrets ms ON m.id = ms.message_id
LEFT JOIN whatsmeow_contacts c ON ms.sender_jid = c.their_jid
WHERE m.chat_jid = '120363049581425328@g.us'
  AND m.timestamp >= datetime('now', '-7 days')
ORDER BY m.timestamp DESC
LIMIT 20;
```

## Performance Considerations

### Indexing Recommendations
```sql
-- For faster message-to-sender lookups
CREATE INDEX IF NOT EXISTS idx_message_secrets_lookup 
ON whatsmeow_message_secrets(message_id, chat_jid);

-- For faster contact name resolution
CREATE INDEX IF NOT EXISTS idx_contacts_jid 
ON whatsmeow_contacts(their_jid);

-- For faster message queries by chat
CREATE INDEX IF NOT EXISTS idx_messages_chat_time 
ON messages(chat_jid, timestamp);
```

### Query Optimization Tips
1. **Use JOINs carefully**: Cross-database JOINs can be expensive, especially with large message histories
2. **Limit date ranges**: Always include timestamp filters when querying messages
3. **Cache contact information**: Build an in-memory cache of contact JIDs to names for frequent lookups
4. **Use prepared statements**: For repeated queries to avoid parsing overhead

## Quick Reference

### Database Files
- **`store/whatsapp.db`** - Device config, contacts, cryptographic data
- **`store/messages.db`** - Chat metadata and message storage

### Key Statistics (Example Dataset)
- **Total Contacts**: 2,613
- **Active Chats**: 124 (3 groups, 121 individual)
- **Database Size**: ~50MB combined

## Common Use Cases

### 1. Extract All Chats with Names

**Goal**: Get a complete list of all WhatsApp chats with proper display names.

**Python Implementation**:
```python
import sqlite3

def get_all_chats_with_names():
    whatsapp_conn = sqlite3.connect('store/whatsapp.db')
    messages_conn = sqlite3.connect('store/messages.db')
    
    # Get contacts for name resolution
    contacts_query = """
        SELECT their_jid, first_name, full_name, push_name, business_name
        FROM whatsmeow_contacts
    """
    contacts = {}
    for row in whatsapp_conn.execute(contacts_query):
        jid, first, full, push, business = row
        # Priority: full_name > first_name > push_name > business_name
        name = full or first or push or business or jid.split('@')[0]
        contacts[jid] = name
    
    # Get all chats
    chats_query = """
        SELECT jid, name, last_message_time
        FROM chats
        ORDER BY last_message_time DESC
    """
    
    results = []
    for jid, name, last_time in messages_conn.execute(chats_query):
        display_name = contacts.get(jid, name or jid.split('@')[0])
        chat_type = 'Group' if '@g.us' in jid else 'Individual'
        
        results.append({
            'jid': jid,
            'name': display_name,
            'type': chat_type,
            'last_activity': last_time
        })
    
    whatsapp_conn.close()
    messages_conn.close()
    return results
```

### 2. Group vs Individual Chat Analysis

**SQL Query**:
```sql
-- Count chats by type
SELECT 
    CASE 
        WHEN jid LIKE '%@g.us' THEN 'Groups'
        WHEN jid = 'status@broadcast' THEN 'Status'
        ELSE 'Individual'
    END as chat_type,
    COUNT(*) as count
FROM chats
GROUP BY chat_type;
```

### 3. Recent Activity Analysis

**SQL Query**:
```sql
-- Get most active chats in last 7 days
SELECT 
    name,
    jid,
    last_message_time,
    CASE WHEN jid LIKE '%@g.us' THEN 'Group' ELSE 'Individual' END as type
FROM chats 
WHERE last_message_time > datetime('now', '-7 days')
ORDER BY last_message_time DESC
LIMIT 10;
```

### 4. Contact Information Lookup

**Python Function**:
```python
def find_contact_by_name(search_term):
    conn = sqlite3.connect('store/whatsapp.db')
    query = """
        SELECT their_jid, first_name, full_name, push_name, business_name
        FROM whatsmeow_contacts
        WHERE full_name LIKE ? OR first_name LIKE ? OR push_name LIKE ?
        ORDER BY full_name, first_name, push_name
    """
    
    search_pattern = f"%{search_term}%"
    results = conn.execute(query, (search_pattern, search_pattern, search_pattern)).fetchall()
    conn.close()
    return results
```

## Data Export Patterns

### 1. CSV Export of All Chats

```python
import csv
from datetime import datetime

def export_chats_to_csv(filename=None):
    if not filename:
        filename = f"whatsapp_chats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    chats = get_all_chats_with_names()  # From previous example
    
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['jid', 'name', 'type', 'last_activity']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for chat in chats:
            writer.writerow(chat)
    
    return filename
```

### 2. JSON Export with Metadata

```python
import json

def export_database_summary():
    whatsapp_conn = sqlite3.connect('store/whatsapp.db')
    messages_conn = sqlite3.connect('store/messages.db')
    
    # Get counts
    contact_count = whatsapp_conn.execute("SELECT COUNT(*) FROM whatsmeow_contacts").fetchone()[0]
    chat_count = messages_conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
    group_count = messages_conn.execute("SELECT COUNT(*) FROM chats WHERE jid LIKE '%@g.us'").fetchone()[0]
    
    # Get recent activity
    recent_chats = messages_conn.execute("""
        SELECT name, last_message_time 
        FROM chats 
        ORDER BY last_message_time DESC 
        LIMIT 5
    """).fetchall()
    
    summary = {
        'export_time': datetime.now().isoformat(),
        'statistics': {
            'total_contacts': contact_count,
            'total_chats': chat_count,
            'groups': group_count,
            'individual_chats': chat_count - group_count
        },
        'recent_activity': [
            {'name': name, 'last_message': time} 
            for name, time in recent_chats
        ]
    }
    
    whatsapp_conn.close()
    messages_conn.close()
    
    with open('whatsapp_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    return summary
```

## Database Maintenance

### 1. Check Database Integrity

```bash
# Check whatsapp.db
sqlite3 store/whatsapp.db "PRAGMA integrity_check;"

# Check messages.db
sqlite3 store/messages.db "PRAGMA integrity_check;"
```

### 2. Database Size Analysis

```sql
-- Get table sizes (approximate)
SELECT 
    name,
    COUNT(*) as row_count
FROM sqlite_master 
WHERE type='table' 
AND name NOT LIKE 'sqlite_%';

-- For each table, run:
SELECT COUNT(*) FROM table_name;
```

### 3. Backup Strategy

```bash
# Create backups
cp store/whatsapp.db "backups/whatsapp_$(date +%Y%m%d_%H%M%S).db"
cp store/messages.db "backups/messages_$(date +%Y%m%d_%H%M%S).db"

# Or use SQLite backup command
sqlite3 store/whatsapp.db ".backup backups/whatsapp_backup.db"
```

## Troubleshooting

### 1. Database Locked Errors

```python
import sqlite3
import time

def safe_db_connection(db_path, max_retries=5):
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect(db_path, timeout=30.0)
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                time.sleep(1)
                continue
            raise
```

### 2. Handling Missing Data

```python
def safe_get_display_name(jid, name, contacts_dict):
    """Safely get display name with fallbacks"""
    if jid in contacts_dict:
        return contacts_dict[jid]
    
    if name and name.strip() and name != jid.split('@')[0]:
        return name.strip()
    
    # Extract phone number from JID
    if '@' in jid:
        phone = jid.split('@')[0]
        if phone != 'status':
            return f"📱 {phone}"
    
    return jid  # Ultimate fallback
```

### 3. Character Encoding Issues

```python
# Always use UTF-8 encoding
with open('output.txt', 'w', encoding='utf-8') as f:
    f.write(text)

# For CSV files
import csv
with open('output.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile)
```

## Security Considerations

1. **Database Access**: These databases contain sensitive personal information
2. **Backup Security**: Encrypt backups if storing externally
3. **Access Control**: Limit file system permissions on database files
4. **Data Retention**: Consider data retention policies for exports

## Practical Database Insights

### Contact Name Resolution Priority
When displaying contact names, use this priority order:
1. `full_name` from `whatsmeow_contacts`
2. `first_name` from `whatsmeow_contacts`
3. `push_name` from `whatsmeow_contacts`
4. `business_name` from `whatsmeow_contacts`
5. `name` from `chats` table
6. Phone number extracted from JID (fallback)

### JID Format Patterns
- **Individual chats**: `[phone_number]@s.whatsapp.net`
- **Group chats**: `[group_id]@g.us`
- **Status broadcasts**: `status@broadcast`
- **International numbers**: Include country code without `+` symbol

### Chat Type Identification
```sql
-- Identify group chats
SELECT * FROM chats WHERE jid LIKE '%@g.us';

-- Identify individual chats (excluding status)
SELECT * FROM chats WHERE jid LIKE '%@s.whatsapp.net';

-- Get status broadcasts
SELECT * FROM chats WHERE jid = 'status@broadcast';
```

## Database Access Examples

### Python SQLite Connection
```python
import sqlite3

# Connect to both databases
whatsapp_conn = sqlite3.connect('store/whatsapp.db')
messages_conn = sqlite3.connect('store/messages.db')

# Example: Get contact count
cursor = whatsapp_conn.cursor()
cursor.execute("SELECT COUNT(*) FROM whatsmeow_contacts")
contact_count = cursor.fetchone()[0]

# Example: Get chat count
cursor = messages_conn.cursor()
cursor.execute("SELECT COUNT(*) FROM chats")
chat_count = cursor.fetchone()[0]
```

### Command Line Access
```bash
# View whatsapp.db tables
sqlite3 store/whatsapp.db ".tables"

# View messages.db schema
sqlite3 store/messages.db ".schema chats"

# Quick chat count
sqlite3 store/messages.db "SELECT COUNT(*) FROM chats;"

# List recent groups
sqlite3 store/messages.db "SELECT name, last_message_time FROM chats WHERE jid LIKE '%@g.us' ORDER BY last_message_time DESC LIMIT 5;"
```

## Technical Glossary Integration

As of August 27, 2025, the system has been enhanced with a comprehensive technical glossary that helps the AI better understand domain-specific terminology in WhatsApp conversations. The `build_technical_glossary.py` script was successfully executed to process all 15,292 messages from 60 WhatsApp groups, generating a rich repository of technical terms, business concepts, and domain-specific ideas.

### Recent Enhancement
The `build_technical_glossary.py` script had a syntax error that was fixed by correcting escaped quotes in docstrings. After the fix, the script ran successfully and generated two output files:
1. `technical_glossary.md` - Human-readable markdown format
2. `technical_glossary_data.json` - Structured JSON data

### Key Technical Terms Recognized (19 total):
- **RCA (Root Cause Analysis)**: Systematic process for identifying the origin of problems, used for investigating technical bugs and operational issues
- **SnP (Scan and Pay)**: UPI QR code payment feature within the app with a focus on user growth through hyperlocal offline stores
- **VPA (Virtual Payment Address)**: Unique identifier used to send and receive money on the UPI platform, with critical management including whitelisting
- **Mapper**: NPCI's Central Mapper linking phone numbers to default VPAs, strategically leveraged for user acquisition
- **Tokenisation**: Process of replacing sensitive card information with unique tokens for in-app and Tap-to-Pay payments
- **PPS (Post Payment Screen)**: Screen appearing after transaction completion, critical for displaying rewards and cross-selling
- **RAPI (Rewards API)**: API allowing partners to integrate with CRED's rewards system for issuing offers
- **ARF (Allotment Rules Framework)**: System replacing Falcon for reward eligibility and allotment
- **CLO/ULO**: Card-Linked/User-Linked Offers for cross-selling and reactivation campaigns
- **BPT (Burn Per Transaction)**: Financial metric tracking cost-efficiency of payment products
- **CCBP (Credit Card Bill Payment)**: Core Line of Business for paying credit card bills through the app
- **MID (Merchant ID)**: Unique identifier for merchants in payment transactions
- **SR (Success Rate)**: KPI measuring percentage of successful transaction outcomes
- **MTU**: Monthly Transacting Users metric for tracking user engagement
- **API (Application Programming Interface)**: Protocols for software communication between systems
- **DAG**: Directed Acyclic Graph data pipeline architecture for campaign data processing
- **act-react**: Activation and reactivation strategies for user engagement
- **LOB**: Line of Business product verticals (CCBP, SnP, Pay Online)
- **UCMS**: Unified Campaign Management System replacing fragmented tools

### Business Concepts Integrated (9 total):
- Settlement and reconciliation processes with fallback mechanisms for data pipeline failures
- User segmentation strategies with explicit SQL-like logic defining ETU and Zombie users
- Partner-funded cashback models with C1/C2 cohort data sharing via SFTP
- Multi-LOB adoption initiatives to convert single-LOB users to multi-LOB engagement
- Data pipeline reliability mechanisms with automated fallback logic for campaign continuity
- Burn management and campaign ROI optimization with focus on cost-per-transaction metrics
- WBR/MBR (Weekly/Monthly Business Review) processes including RCAs and recommendations
- VPA Whitelisting operational procedures for accurate merchant transaction tracking
- User Reactivation (Zombie Campaigns) strategies including gift card offers and CLO/ULO

### Domain-Specific Ideas & Innovations (7 total):
- Leveraging NPCI Mapper for User Acquisition by encouraging users to set CRED as default
- Coinpay Flow for Zombie Reactivation without complex API integration, showing 22% conversion
- P2P Receiver-Side Nudges for Zombie Reactivation at moment of receiving money
- Unified Campaign Management System (UCMS) centralizing Falcon, Win, Midas tools
- Hyperlocal Offline Store Expansion strategy with thousands of partner stores
- Rupay 1% Rewards Program (UPI 2.0) as proof of concept for RuPay card adoption
- Device Tokenization as a Strategic Moat and organizational priority for secure checkouts
- P2P Receipt Gamification for Viral Growth with premium designs for affluent users
- Assured Cashback with Widget Campaigns showing 20% lift in activation rates

This integration allows the AI components to better understand and process WhatsApp conversations that contain these specialized terms, leading to more accurate task identification and more contextually appropriate responses. The glossary is regularly updated through the `build_technical_glossary.py` script which processes messages from all monitored WhatsApp groups.