import os
import json
from datetime import datetime
from typing import List, Dict, Any
from langchain_core.tools import tool

CALENDAR_FILE = "calendar.json"

def _load_calendar() -> List[Dict[str, Any]]:
    if not os.path.exists(CALENDAR_FILE):
        default_events = [
            {
                "id": "1",
                "title": "Weekly Standup",
                "start": "2026-07-22 09:00:00",
                "end": "2026-07-22 09:30:00",
                "description": "Weekly alignment with engineering team."
            }
        ]
        _save_calendar(default_events)
        return default_events
    try:
        with open(CALENDAR_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return []

def _save_calendar(data: List[Dict[str, Any]]):
    with open(CALENDAR_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@tool
def list_calendar_events() -> str:
    """Retrieves all upcoming events from the calendar."""
    events = _load_calendar()
    if not events:
        return "Your calendar is clear."
    
    result = []
    for event in events:
        result.append(f"ID: {event['id']}\nEvent: {event['title']}\nStart: {event['start']}\nEnd: {event['end']}\nDescription: {event['description']}\n---")
    return "\n".join(result)

@tool
def schedule_event(title: str, start_time: str, end_time: str, description: str = "") -> str:
    """Schedules a new event on the calendar. Expects start_time and end_time in YYYY-MM-DD HH:MM:SS format."""
    events = _load_calendar()
    new_event = {
        "id": str(len(events) + 1),
        "title": title,
        "start": start_time,
        "end": end_time,
        "description": description
    }
    events.append(new_event)
    _save_calendar(events)
    return f"Successfully scheduled '{title}' from {start_time} to {end_time}."
