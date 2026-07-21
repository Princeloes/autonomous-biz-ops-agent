import os
import json
from datetime import datetime
from typing import List, Dict, Any
from langchain_core.tools import tool

MAILBOX_FILE = "mailbox.json"

def _load_mailbox() -> List[Dict[str, Any]]:
    if not os.path.exists(MAILBOX_FILE):
        # Create a default inbox with some initial messages
        default_inbox = [
            {
                "id": "1",
                "from": "manager@enterprise.com",
                "subject": "Q3 Planning Update Needed",
                "body": "Hi, I need you to gather research on LangGraph and Langfuse, draft a summary report, and schedule a review meeting on my calendar for next Monday at 10 AM. Thanks!",
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "unread"
            }
        ]
        _save_mailbox(default_inbox)
        return default_inbox
    try:
        with open(MAILBOX_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def _save_mailbox(data: List[Dict[str, Any]]):
    with open(MAILBOX_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@tool
def list_emails() -> str:
    """Retrieves all emails in the inbox."""
    emails = _load_mailbox()
    if not emails:
        return "Your inbox is empty."
    
    result = []
    for email in emails:
        status_flag = "[UNREAD] " if email.get("status") == "unread" else ""
        result.append(f"ID: {email['id']}\nFrom: {email['from']}\nSubject: {status_flag}{email['subject']}\nDate: {email['date']}\nBody: {email['body']}\n---")
    return "\n".join(result)

@tool
def send_email(to_address: str, subject: str, body: str) -> str:
    """Sends an email to the specified address with the given subject and body."""
    emails = _load_mailbox()
    new_email = {
        "id": str(len(emails) + 1),
        "from": "ai-employee@enterprise.com",
        "to": to_address,
        "subject": subject,
        "body": body,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "sent"
    }
    emails.append(new_email)
    _save_mailbox(emails)
    return f"Email successfully sent to {to_address} with subject: '{subject}'."

@tool
def mark_as_read(email_id: str) -> str:
    """Marks a specific email as read."""
    emails = _load_mailbox()
    for email in emails:
        if email["id"] == email_id:
            email["status"] = "read"
            _save_mailbox(emails)
            return f"Email {email_id} marked as read."
    return f"Email with ID {email_id} not found."
