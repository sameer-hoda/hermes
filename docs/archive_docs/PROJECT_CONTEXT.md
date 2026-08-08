# WhatsApp Task God v1 - Project Context

## Overview
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

This integration allows the AI components to better understand and process WhatsApp conversations that contain these specialized terms, leading to more accurate task identification and more contextually appropriate responses. The glossary is regularly updated through the `build_technical_glossary.py` script which processes messages from all monitored WhatsApp groups.