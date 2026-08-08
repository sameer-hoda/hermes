# WhatsApp Bridge Database Schema Documentation

This document provides a comprehensive overview of the database schema used in the WhatsApp bridge project. It details the structure, relationships, and purpose of all tables in both databases.

## Database Overview

The WhatsApp bridge uses two SQLite databases:

1. **`whatsapp.db`** - Contains device configuration, cryptographic data, contacts, and session information
2. **`messages.db`** - Contains chat metadata and message content

This separation allows for better organization and performance, with configuration data separate from the potentially large message history.

## Database Relationships Diagram

```
┌─────────────────────────┐                 ┌─────────────────────────┐
│      whatsapp.db        │                 │       messages.db       │
├─────────────────────────┤                 ├─────────────────────────┤
│ whatsmeow_device        │                 │ chats                   │
│  - jid (PK)             │◄────────┐       │  - jid (PK)             │
│  - registration_id      │         │       │  - name                 │
│  - noise_key            │         │       │  - last_message_time    │
│  - identity_key         │         │       │                         │
│  - ...                  │         │       │                         │
└─────────────────────────┘         │       └───────────┬─────────────┘
          ▲                         │                   │
          │                         │                   │
┌─────────┴─────────────┐          │       ┌───────────▼─────────────┐
│ whatsmeow_contacts    │          │       │ messages                │
│  - our_jid (PK)(FK)   │          │       │  - id (PK)              │
│  - their_jid (PK)     │          │       │  - chat_jid (PK)(FK)    │
│  - first_name         │          │       │  - sender               │
│  - full_name          │          │       │  - content              │
│  - push_name          │          │       │  - timestamp            │
│  - business_name      │          │       │  - is_from_me           │
└─────────┬─────────────┘          │       │  - media_type           │
          │                        │       │  - ...                  │
          │                        │       └───────────┬─────────────┘
┌─────────▼─────────────┐          │                   │
│ whatsmeow_message_    │          │                   │
│ secrets               │          │                   │
│  - our_jid (PK)(FK)   │◄─────────┘                   │
│  - chat_jid (PK)      │◄───────────────────────────┐ │
│  - sender_jid (PK)    │◄─────────┐                 │ │
│  - message_id (PK)    │◄─────────┼─────────────────┼─┘
│  - key                │          │                 │
└─────────────────────┬─┘          │                 │
                      │            │                 │
                      │            │                 │
                      ▼            ▼                 ▼
             Resolves actual   Maps to actual    Links to message
             sender in groups  contact info      in messages.db
```

## Database 1: `whatsapp.db`

### Core Tables

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

### Cryptographic and Session Tables

#### `whatsmeow_identity_keys`
Stores identity keys for contacts.

| Field Name | Type  | Description                                           |
|------------|-------|-------------------------------------------------------|
| our_jid    | TEXT  | **Primary Key (1).** JID of our device (FK).          |
| their_id   | TEXT  | **Primary Key (2).** Identifier for the other party.  |
| identity   | bytea | 32-byte identity key of the other party.              |

**Purpose**: Maintains the identity keys of contacts for end-to-end encryption verification.

#### `whatsmeow_pre_keys`
Stores pre-keys for session establishment.

| Field Name | Type    | Description                                         |
|------------|---------|-----------------------------------------------------|
| jid        | TEXT    | **Primary Key (1).** JID of our device (FK).        |
| key_id     | INTEGER | **Primary Key (2).** ID of the pre-key.             |
| key        | bytea   | 32-byte pre-key for session establishment.          |
| uploaded   | BOOLEAN | True if the pre-key has been uploaded to the server.|

**Purpose**: Manages pre-keys used in the Signal protocol for establishing secure sessions.

#### `whatsmeow_sessions`
Stores session information for conversations.

| Field Name | Type  | Description                                           |
|------------|-------|-------------------------------------------------------|
| our_jid    | TEXT  | **Primary Key (1).** JID of our device (FK).          |
| their_id   | TEXT  | **Primary Key (2).** Identifier for the other party.  |
| session    | bytea | Serialized session state for secure communication.    |

**Purpose**: Maintains encrypted session data for ongoing conversations.

#### `whatsmeow_sender_keys`
Stores sender keys for group message encryption.

| Field Name | Type  | Description                                           |
|------------|-------|-------------------------------------------------------|
| our_jid    | TEXT  | **Primary Key (1).** JID of our device (FK).          |
| chat_id    | TEXT  | **Primary Key (2).** JID of the chat (group).         |
| sender_id  | TEXT  | **Primary Key (3).** JID of the sender in the chat.   |
| sender_key | bytea | Sender key for group message encryption.              |

**Purpose**: Manages keys for the Signal protocol's group messaging encryption.

### App State and Settings Tables

#### `whatsmeow_app_state_sync_keys`
Stores keys for app state synchronization.

| Field Name   | Type   | Description                                        |
|--------------|--------|----------------------------------------------------|
| jid          | TEXT   | **Primary Key (1).** JID of our device (FK).       |
| key_id       | bytea  | **Primary Key (2).** Identifier for the sync key.  |
| key_data     | bytea  | The sync key data.                                 |
| timestamp    | BIGINT | Timestamp when the key was created/updated.        |
| fingerprint  | bytea  | Fingerprint of the sync key.                       |

**Purpose**: Manages synchronization keys for WhatsApp's app state.

#### `whatsmeow_app_state_version`
Tracks versions of different app state components.

| Field Name | Type   | Description                                          |
|------------|--------|------------------------------------------------------|
| jid        | TEXT   | **Primary Key (1).** JID of our device (FK).         |
| name       | TEXT   | **Primary Key (2).** Name of the app state.          |
| version    | BIGINT | Version number of the app state.                     |
| hash       | bytea  | 128-byte hash of the app state.                      |

**Purpose**: Tracks the version of different components of the app state.

#### `whatsmeow_app_state_mutation_macs`
Stores MACs for app state mutations.

| Field Name | Type   | Description                                          |
|------------|--------|------------------------------------------------------|
| jid        | TEXT   | **Primary Key (1).** JID of our device (FK).         |
| name       | TEXT   | **Primary Key (2).** Name of the app state.          |
| version    | BIGINT | **Primary Key (3).** Version number of the mutation. |
| index_mac  | bytea  | **Primary Key (4).** 32-byte MAC for mutation index. |
| value_mac  | bytea  | 32-byte MAC for the mutation value.                  |

**Purpose**: Maintains Message Authentication Codes for app state mutations.

#### `whatsmeow_chat_settings`
Stores user-specific chat settings including archive status.

| Field Name   | Type    | Description                                        |
|--------------|--------|----------------------------------------------------|
| our_jid      | TEXT    | **Primary Key (1).** JID of our device (FK).       |
| chat_jid     | TEXT    | **Primary Key (2).** JID of the chat.              |
| muted_until  | BIGINT  | Timestamp until which the chat is muted.           |
| pinned       | BOOLEAN | True if the chat is pinned.                        |
| archived     | BOOLEAN | **True if the chat is archived, false otherwise.** |

**Purpose**: Stores user preferences for individual chats, including archive status which is critical for determining if a chat has been archived by the user.

**Archive Detection**: The `archived` field is the definitive way to detect if a WhatsApp chat has been archived. A value of `1` (true) indicates the chat is archived, while `0` (false) indicates it is not archived.

#### `whatsmeow_privacy_tokens`
Stores privacy tokens for communication.

| Field Name | Type   | Description                                          |
|------------|--------|------------------------------------------------------|
| our_jid    | TEXT   | **Primary Key (1).** JID of our device.              |
| their_jid  | TEXT   | **Primary Key (2).** JID of the other party.         |
| token      | bytea  | Privacy token for communication.                     |
| timestamp  | BIGINT | Timestamp when the token was created/updated.        |

**Purpose**: Manages privacy tokens used in WhatsApp's communication protocol.

#### `whatsmeow_version`
Stores the database schema version.

| Field Name | Type    | Description                                         |
|------------|---------|-----------------------------------------------------|
| version    | INTEGER | The schema version of the database.                 |

**Purpose**: Tracks the schema version for compatibility and migrations.

## Database 2: `messages.db`

### Core Tables

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

## JID Format Patterns

Understanding JID formats is crucial for working with these databases:

- **Individual chats**: `[phone_number]@s.whatsapp.net` (e.g., `919876543210@s.whatsapp.net`)
- **Group chats**: `[group_id]@g.us` (e.g., `120363049581425328@g.us`)
- **Status broadcasts**: `status@broadcast`
- **Device JIDs**: `[phone_number]:[device_id]@s.whatsapp.net` (e.g., `919876543210:4@s.whatsapp.net`)

## Common Query Patterns

### 1. Get Messages with Proper Sender Names in Group Chats

```sql
SELECT 
    m.id,
    m.content,
    m.timestamp,
    COALESCE(
        c.full_name,
        c.first_name,
        c.push_name,
        c.business_name,
        SUBSTR(ms.sender_jid, 1, INSTR(ms.sender_jid, '@') - 1)
    ) as sender_name,
    m.is_from_me
FROM messages m
JOIN whatsmeow_message_secrets ms ON (
    m.id = ms.message_id AND 
    m.chat_jid = ms.chat_jid
)
LEFT JOIN whatsmeow_contacts c ON ms.sender_jid = c.their_jid
WHERE m.chat_jid = '120363049581425328@g.us'
ORDER BY m.timestamp ASC;
```

### 2. Get All Chats with Proper Contact Names

```sql
SELECT 
    c.jid,
    COALESCE(
        contacts.full_name,
        contacts.first_name,
        contacts.push_name,
        contacts.business_name,
        c.name,
        SUBSTR(c.jid, 1, INSTR(c.jid, '@') - 1)
    ) as display_name,
    c.last_message_time,
    CASE 
        WHEN c.jid LIKE '%@g.us' THEN 'Group'
        WHEN c.jid = 'status@broadcast' THEN 'Status'
        ELSE 'Individual'
    END as chat_type
FROM chats c
LEFT JOIN whatsmeow_contacts contacts ON c.jid = contacts.their_jid
ORDER BY c.last_message_time DESC;
```

### 3. Count Messages by Sender in a Group

```sql
SELECT 
    COALESCE(c.full_name, c.push_name, c.first_name, 
             SUBSTR(ms.sender_jid, 1, INSTR(ms.sender_jid, '@') - 1)) as sender_name,
    COUNT(*) as message_count
FROM messages m
JOIN whatsmeow_message_secrets ms ON m.id = ms.message_id AND m.chat_jid = ms.chat_jid
LEFT JOIN whatsmeow_contacts c ON ms.sender_jid = c.their_jid
WHERE m.chat_jid = '120363049581425328@g.us'
GROUP BY ms.sender_jid
ORDER BY message_count DESC;
```

### 4. Get All Archived Chats

```sql
SELECT 
    cs.chat_jid,
    COALESCE(
        contacts.full_name,
        contacts.first_name,
        contacts.push_name,
        contacts.business_name,
        c.name,
        SUBSTR(cs.chat_jid, 1, INSTR(cs.chat_jid, '@') - 1)
    ) as display_name,
    cs.archived,
    cs.pinned,
    cs.muted_until,
    c.last_message_time
FROM whatsmeow_chat_settings cs
LEFT JOIN chats c ON cs.chat_jid = c.jid
LEFT JOIN whatsmeow_contacts contacts ON cs.chat_jid = contacts.their_jid
WHERE cs.archived = 1
ORDER BY c.last_message_time DESC;
```

### 5. Check if a Specific Chat is Archived

```sql
SELECT 
    cs.chat_jid,
    cs.archived,
    COALESCE(
        contacts.full_name,
        contacts.first_name,
        contacts.push_name,
        c.name,
        SUBSTR(cs.chat_jid, 1, INSTR(cs.chat_jid, '@') - 1)
    ) as display_name
FROM whatsmeow_chat_settings cs
LEFT JOIN chats c ON cs.chat_jid = c.jid
LEFT JOIN whatsmeow_contacts contacts ON cs.chat_jid = contacts.their_jid
WHERE cs.chat_jid = 'CHAT_JID_HERE';
```

## Database Access Patterns

### Python SQLite Connection Example

```python
import sqlite3

def connect_to_databases():
    """Connect to both WhatsApp databases"""
    whatsapp_conn = sqlite3.connect('store/whatsapp.db')
    messages_conn = sqlite3.connect('store/messages.db')
    return whatsapp_conn, messages_conn

def get_messages_with_sender_names(chat_jid):
    """Get messages with proper sender names for a chat"""
    whatsapp_conn, messages_conn = connect_to_databases()
    
    # Attach whatsapp.db to messages connection for cross-database queries
    messages_conn.execute("ATTACH DATABASE 'store/whatsapp.db' AS whatsapp_db")
    
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
        ) as sender_name,
        m.is_from_me
    FROM messages m
    JOIN whatsapp_db.whatsmeow_message_secrets ms ON (
        m.id = ms.message_id AND 
        m.chat_jid = ms.chat_jid
    )
    LEFT JOIN whatsapp_db.whatsmeow_contacts c ON ms.sender_jid = c.their_jid
    WHERE m.chat_jid = ?
    ORDER BY m.timestamp ASC
    """
    
    results = messages_conn.execute(query, (chat_jid,)).fetchall()
    
    whatsapp_conn.close()
    messages_conn.close()
    
    return results
```

## Performance Considerations

### Recommended Indexes

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

## Security Considerations

1. **Database Encryption**: The databases contain sensitive personal information and should be protected
2. **Access Control**: Limit file system permissions on database files
3. **Backup Security**: Encrypt backups if storing externally
4. **Data Retention**: Consider implementing data retention policies

## Conclusion

The WhatsApp bridge database schema is designed to efficiently store both the cryptographic material needed for WhatsApp's end-to-end encryption and the message history. The separation into two databases provides a clean organization, with `whatsapp.db` handling device configuration and contacts, while `messages.db` focuses on chat and message storage.

The most complex aspect is the resolution of message senders in group chats, which requires joining data across both databases. Understanding these relationships is crucial for correctly displaying and analyzing WhatsApp conversations.
