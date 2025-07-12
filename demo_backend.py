#!/usr/bin/env python3
"""
Demo Calendar Backend

Mock backend server for Google Calendar integration demos.
Simulates the real Omi backend for testing purposes.
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
import uvicorn
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json
import random
import time

app = FastAPI(title="Omi Calendar Demo Backend")

# Demo statistics
demo_stats = {
    "total_requests": 0,
    "successful_requests": 0,
    "failed_requests": 0,
    "events_created": 0
}

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "calendar_available": True,
        "demo_mode": True,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/v1/calendar/auth")
def initiate_google_auth():
    """Mock OAuth initiation"""
    demo_stats["total_requests"] += 1
    demo_stats["successful_requests"] += 1
    
    return {
        "auth_url": "https://accounts.google.com/oauth/authorize?mock=true",
        "demo_mode": True,
        "message": "This is a mock OAuth URL for demo purposes"
    }

@app.get("/v1/calendar/status")
def get_calendar_status():
    """Mock calendar status"""
    demo_stats["total_requests"] += 1
    demo_stats["successful_requests"] += 1
    
    return {
        "connected": True,
        "calendar_name": "Demo Calendar",
        "timezone": "America/New_York",
        "demo_mode": True,
        "events_created": demo_stats["events_created"],
        "last_updated": datetime.now().isoformat()
    }

@app.post("/v1/calendar/events")
def create_calendar_event(event: Dict[str, Any]):
    """Mock event creation with realistic delays"""
    demo_stats["total_requests"] += 1
    
    # Simulate some processing time
    processing_delay = random.uniform(0.05, 0.3)  # 50-300ms
    time.sleep(processing_delay)
    
    # Simulate occasional failures (5% failure rate)
    if random.random() < 0.05:
        demo_stats["failed_requests"] += 1
        raise HTTPException(status_code=500, detail="Simulated network error")
    
    demo_stats["successful_requests"] += 1
    demo_stats["events_created"] += 1
    
    # Generate mock event response
    event_id = f"demo_event_{demo_stats['events_created']}_{int(time.time())}"
    
    return {
        "message": "Event created successfully (demo mode)",
        "event": {
            "id": event_id,
            "title": event.get("title", "Demo Event"),
            "start_time": event.get("start_time"),
            "end_time": event.get("end_time", 
                datetime.fromisoformat(event.get("start_time", datetime.now().isoformat()).replace('Z', '')) + timedelta(hours=1)
            ),
            "demo_mode": True,
            "created_at": datetime.now().isoformat(),
            "response_time_ms": int(processing_delay * 1000)
        }
    }

@app.get("/v1/calendar/events")
def get_calendar_events(days_ahead: int = Query(7)):
    """Mock event retrieval"""
    demo_stats["total_requests"] += 1
    demo_stats["successful_requests"] += 1
    
    # Generate some mock events
    events = []
    now = datetime.now()
    
    for i in range(min(demo_stats["events_created"], 10)):
        event_time = now + timedelta(hours=i*2)
        events.append({
            "id": f"demo_event_{i}",
            "title": f"Demo Event {i+1}",
            "start_time": event_time.isoformat(),
            "end_time": (event_time + timedelta(hours=1)).isoformat(),
            "demo_mode": True
        })
    
    return {
        "events": events,
        "total_count": len(events),
        "demo_mode": True
    }

@app.get("/v1/calendar/test")
def test_calendar_integration():
    """Mock test endpoint"""
    demo_stats["total_requests"] += 1
    demo_stats["successful_requests"] += 1
    
    return {
        "status": "success",
        "message": "Demo calendar integration test successful",
        "demo_mode": True,
        "stats": demo_stats,
        "timestamp": datetime.now().isoformat()
    }

@app.get("/stats")
def get_demo_stats():
    """Get demo statistics"""
    return {
        "demo_stats": demo_stats,
        "success_rate": (demo_stats["successful_requests"] / max(demo_stats["total_requests"], 1)) * 100,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/reset-stats")
def reset_demo_stats():
    """Reset demo statistics"""
    global demo_stats
    demo_stats = {
        "total_requests": 0,
        "successful_requests": 0,
        "failed_requests": 0,
        "events_created": 0
    }
    return {"message": "Demo statistics reset", "stats": demo_stats}

def main():
    """Start the demo backend"""
    print("🚀 Starting Omi Calendar Demo Backend...")
    print("📅 Demo mode: Calendar events are simulated")
    print("🌐 Server will start on http://localhost:8000")
    print("📋 Available endpoints:")
    print("   - GET /health")
    print("   - GET /v1/calendar/auth")
    print("   - GET /v1/calendar/status")
    print("   - POST /v1/calendar/events")
    print("   - GET /v1/calendar/events")
    print("   - GET /v1/calendar/test")
    print("   - GET /stats")
    print("   - POST /reset-stats")
    print("\n✅ This is a DEMO backend - events are simulated!")
    print("🔗 For real calendar testing, use: python3 direct_calendar_test.py")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")

if __name__ == "__main__":
    main()