# Contact Resolution Guide

This document provides a comprehensive guide on how to trace and resolve contact names from the various identifiers found in the WhatsApp databases (`whatsapp.db` and `messages.db`).

## 1. Overview of Identifiers

There are three main types of identifiers you will encounter for a user:

*   **JID (Jabber ID):** The primary identifier for a WhatsApp user, in the format `[phone_number]@s.whatsapp.net`. For example: `91XXXXXXXXXX@s.whatsapp.net`.
*   **LID (Local ID):** A numerical identifier that WhatsApp uses internally. These are often seen in the AI model's output when it extracts a "person" from a message. For example: `219541632213229`.
*   **Phone Number:** The user's phone number, usually with the country code. For example: `91XXXXXXXXXX`.

## 2. Key Database Tables

The following tables are crucial for contact resolution:

*   `whatsapp.db`:
    *   `whatsmeow_contacts`: The main table containing contact information, including `their_jid`, `push_name`, `full_name`, `first_name`, and `business_name`.
    *   `whatsmeow_lid_map`: The table that maps LIDs to phone numbers (`pn`).
    *   `whatsmeow_message_secrets`: This table links a message in a group chat to the actual sender's JID.
*   `messages.db`:
    *   `messages`: Contains the message content. In group chats, the `sender` column is the group's JID, not the user's.
    *   `chats`: Contains information about each chat, including the chat JID and name.

## 3. Contact Resolution Flow

The goal is to get a JID, which can then be used to query the `whatsmeow_contacts` table for a name. Here is the resolution flow depending on the identifier you have:

### Case 1: You have a LID

This is the most common case for unresolved contacts in the AI output.

1.  **LID to Phone Number:** Query the `whatsmeow_lid_map` table to find the phone number (`pn`) associated with the `lid`.
2.  **Phone Number to JID:** Construct the JID by appending `@s.whatsapp.net` to the phone number.
3.  **JID to Name:** Query the `whatsmeow_contacts` table with the JID to get the name.

**SQL Example:**

```sql
-- Step 1: Get phone number from LID
SELECT pn FROM whatsmeow_lid_map WHERE lid = '219541632213229';
-- This will return '91XXXXXXXXXX'

-- Step 2: Use the phone number to get the name
SELECT push_name, full_name, first_name FROM whatsmeow_contacts WHERE their_jid = '91XXXXXXXXXX@s.whatsapp.net';
```

### Case 2: You have a Phone Number

1.  **Phone Number to JID:** Construct the JID by appending `@s.whatsapp.net` to the phone number.
2.  **JID to Name:** Query the `whatsmeow_contacts` table with the JID to get the name.

**SQL Example:**

```sql
SELECT push_name, full_name, first_name FROM whatsmeow_contacts WHERE their_jid = '91XXXXXXXXXX@s.whatsapp.net';
```

### Case 3: You have a JID

This is the most direct case.

1.  **JID to Name:** Query the `whatsmeow_contacts` table with the JID to get the name.

**SQL Example:**

```sql
SELECT push_name, full_name, first_name FROM whatsmeow_contacts WHERE their_jid = '91XXXXXXXXXX@s.whatsapp.net';
```

## 4. Name Resolution Priority

When querying the `whatsmeow_contacts` table, you should prioritize the name fields in the following order, as some fields might be empty:

1.  `push_name`: The user's display name on WhatsApp. This is often the most reliable.
2.  `full_name`: The full name from your contacts.
3.  `first_name`: The first name from your contacts.
4.  `business_name`: If it's a business account.

**SQL `COALESCE` Example:**

```sql
SELECT COALESCE(push_name, full_name, first_name, business_name) as display_name
FROM whatsmeow_contacts
WHERE their_jid = '91XXXXXXXXXX@s.whatsapp.net';
```

## 5. Python Implementation

Here is a Python function that encapsulates the complete logic:

```python
import sqlite3
import os

def resolve_contact_name(identifier):
    """
    Resolves a JID, LID, or phone number to a human-readable name.
    """
    if not identifier:
        return identifier

    whatsapp_db_path = os.path.join('reference', 'store', 'whatsapp.db')
    if not os.path.exists(whatsapp_db_path):
        return f"Database not found at {whatsapp_db_path}"

    try:
        conn = sqlite3.connect(whatsapp_db_path)
        cursor = conn.cursor()

        jid = None

        # Check if it's a LID
        if isinstance(identifier, str) and identifier.isdigit():
            cursor.execute("SELECT pn FROM whatsmeow_lid_map WHERE lid = ?", (identifier,))
            result = cursor.fetchone()
            if result and result[0]:
                jid = f"{result[0]}@s.whatsapp.net"
            else:
                # Assume it's a phone number
                jid = f"{identifier}@s.whatsapp.net"
        elif isinstance(identifier, str) and identifier.endswith('@s.whatsapp.net'):
            jid = identifier
        else:
            # Not a format we can process
            conn.close()
            return identifier

        if not jid:
            conn.close()
            return identifier

        # Query for the name using the JID
        query = """
        SELECT COALESCE(push_name, full_name, first_name, business_name) as name
        FROM whatsmeow_contacts
        WHERE their_jid = ?
        LIMIT 1
        """
        cursor.execute(query, (jid,))
        result = cursor.fetchone()
        conn.close()

        if result and result[0]:
            return result[0]
        else:
            return identifier

    except Exception as e:
        return f"An error occurred: {e}"

# Example Usage:
# print(resolve_contact_name("219541632213229"))  # LID
# print(resolve_contact_name("91XXXXXXXXXX"))      # Phone Number
# print(resolve_contact_name("91XXXXXXXXXX@s.whatsapp.net")) # JID
```
