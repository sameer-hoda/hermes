# Technical Glossary Documentation

## Overview

This document provides a comprehensive reference for the technical glossary integrated into the WhatsApp Task God v1 system. The glossary helps the AI components better understand domain-specific terminology in WhatsApp conversations, leading to more accurate task identification and contextually appropriate responses.

The glossary is automatically generated and updated by the `build_technical_glossary.py` script, which analyzes messages from all monitored WhatsApp groups to identify and define key technical terms, business concepts, and domain-specific innovations.

## Structure

The technical glossary is organized into three main categories:

1. **Technical Terms & Jargon** - Domain-specific terminology and acronyms
2. **Business Concepts & Processes** - Organizational practices and strategies
3. **Domain-Specific Ideas & Innovations** - Strategic initiatives and product concepts

## Key Technical Terms

### Project Management & Operations
- **RCA (Root Cause Analysis)**: Systematic process used in software development and operations to identify the fundamental cause of a problem or incident to prevent its recurrence.

### Payment Systems
- **SnP (Scan and Pay)**: A feature allowing users to make payments by scanning a QR code, typically a UPI QR code.
- **VPA (Virtual Payment Address)**: A unique identifier used in the Unified Payments Interface (UPI) system to send and receive money.
- **NPCI Mapper / Central Mapper**: A centralized database maintained by the National Payments Corporation of India (NPCI) that maps a user's mobile number to a default VPA/bank account.
- **MID (Merchant ID)**: A unique identifier assigned to a merchant by a payment processor or acquirer bank.

### UI/UX & Product
- **PPS (Post Payment Screen)**: The user interface screen displayed immediately after a user completes a payment transaction.

### Backend Systems
- **ARF (Allotment Rules Framework)**: An internal system or framework responsible for determining reward eligibility and allotting rewards based on transaction parameters.
- **Falcon**: An internal system used for campaign management and setting up offers, likely a predecessor to ARF.

### Payment Security
- **Tokenization**: A security process that replaces sensitive card details with a unique digital identifier called a 'token'.

### Data Analytics
- **SR (Success Rate)**: A key performance indicator (KPI) measuring the percentage of successful outcomes.
- **MTU**: Monthly Transacting Users. A metric that counts the number of unique users who perform at least one transaction within a calendar month.
- **DRR**: Daily Run Rate. A performance metric that projects future outcomes based on the current day's performance.

### Software Development
- **API (Application Programming Interface)**: A set of rules and protocols that allows different software applications to communicate with each other.

### Data Engineering
- **DAG (Directed Acyclic Graph)**: A data pipeline architecture used for orchestrating and scheduling complex data processing workflows.

### User Growth & Marketing
- **act-react**: An abbreviation for 'Activation and Reactivation,' referring to the process of acquiring new users or re-engaging dormant/inactive users.

### Financial Metrics
- **BPT**: Burn Per Transaction. A cost-efficiency metric that calculates the average amount of money spent for each transaction processed.

### Business Strategy
- **LOB**: Line of Business. Refers to a specific product vertical or service area within the company.

### Partnerships & Offers
- **CLO / ULO**: Card Linked Offer / UPI Linked Offer. Marketing promotions where discounts or cashback are automatically applied.
- **RAPI**: Rewards API. An Application Programming Interface that allows partner merchants to integrate CRED's rewards.

### Product Features
- **CCBP**: Credit Card Bill Payment. A foundational feature allowing users to pay their credit card bills.

### User Segmentation
- **Zombie / ETU**: User segments based on activity. 'Zombie' refers to inactive users. 'ETU' (Early To Use) refers to new or recently activated users.

### Data & Partnerships
- **C1 / C2 Cohorts**: Specific, named user segments shared with external partners for targeted campaigns.

### Internal Tools
- **UCMS**: Unified Campaign Management System. An internal project to create a centralized platform for campaign management.

## Business Concepts

### Settlement and Reconciliation
The process of verifying and matching transactions recorded in the company's system against reports from payment partners and banks.

### User Segmentation (Cohorting)
The practice of dividing users into groups based on shared characteristics or behaviors for targeted marketing campaigns.

### User Reactivation (Zombie Campaigns)
A business strategy focused on re-engaging users who have become inactive ('Zombies').

### VPA Whitelisting
An operational process of adding a merchant's Virtual Payment Address (VPA) to an approved list within the system.

### Partner Funded Cashback (PFCB) / Instant Discount (ID)
A promotional model where a partner merchant funds the cashback or instant discount offered to a user.

### WBR/MBR (Weekly/Monthly Business Review)
A recurring meeting to review key business metrics, performance against goals, and Root Cause Analysis (RCA) for recent issues.

### Multi-LOB Adoption
A key business goal focused on encouraging users who are active in one Line of Business to start using other LOBs.

### Data Pipeline Reliability and Fallback Logic
The business relies heavily on automated daily data pipelines (DAGs) to generate and share user cohorts with partners.

### Partner-Driven User Acquisition (RAPI & CLO)
A core growth strategy involving integration with external partners through technical solutions like Rewards API and Card/UPI Linked Offers.

### Burn Management and Campaign ROI
The team constantly tracks and aims to optimize its marketing spend, referred to as 'burn'.

## Domain-Specific Innovations

### Leveraging NPCI Mapper for User Acquisition
A strategic idea to capitalize on NPCI's mandate for competitors to use the Central Mapper for P2P payments.

### Link and Pay for RuPay Cards
A product feature designed to simplify the onboarding of RuPay credit cards onto the UPI platform.

### Auto-Applied Instant Discount Flow
A partnership model with merchants to build a checkout experience where a CRED-funded Instant Discount is automatically applied.

### Coinpay Flow for Zombie Reactivation
A lightweight, web-based flow used to reactivate dormant users without requiring a full API integration with a partner.

### P2P Receiver-Side Nudges for Zombie Reactivation
A growth idea to reactivate dormant users by targeting them when they receive a P2P payment on CRED UPI.

### Unified Campaign Management System (UCMS)
A strategic internal project to build a centralized platform that consolidates various campaign management tools.

### Hyperlocal Offline Store Expansion
An initiative to drive significant Scan & Pay user growth by scaling up physical presence in retail stores.

### Rupay 1% Rewards Program (UPI 2.0)
A major rewards program being designed for the upcoming 'UPI 2.0' launch.

### Device Tokenization as a Strategic Moat
A core strategic focus on driving the adoption of device tokenization for both Mastercard and Rupay cards.

### P2P Receipt Gamification for Viral Growth
An idea to make Peer-to-Peer payment receipts more engaging and aspirational to drive viral adoption.

## Integration with WhatsApp Task God

The technical glossary is integrated into the WhatsApp Task God system to enhance the AI's understanding of domain-specific conversations. This integration improves:

1. **Task Identification Accuracy**: Better recognition of action items and assignments that use domain-specific terminology
2. **Contextual Responses**: More appropriate and relevant responses when the bot is mentioned in conversations
3. **Thread Analysis**: Enhanced ability to track and summarize complex business discussions
4. **Mention Detection**: Improved understanding of when technical terms in mentions require specific responses

## Maintenance and Updates

The technical glossary is automatically updated by running:
```bash
python build_technical_glossary.py
```

This script:
1. Retrieves messages from all monitored WhatsApp groups
2. Analyzes the messages using Google's Gemini API
3. Identifies and defines technical terms and business concepts
4. Updates the `technical_glossary.md` file
5. Should be run periodically to keep the glossary current with evolving terminology

## File Locations

- **Main Glossary File**: `technical_glossary.md` (project root)
- **Documentation**: `docs/README_TECHNICAL_GLOSSARY.md` (this file)
- **Generation Script**: `build_technical_glossary.py` (project root)

## Usage in Development

Developers can reference this glossary when:
1. Extending the AI analysis capabilities
2. Adding new features that process WhatsApp messages
3. Debugging issues with task identification
4. Improving the bot's response accuracy

The glossary serves as a shared understanding of domain terminology between the development team and the AI systems.