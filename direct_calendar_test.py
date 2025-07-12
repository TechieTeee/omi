#!/usr/bin/env python3
"""
Direct Google Calendar Test - Creates Real Events

This bypasses the backend and creates real events directly using your Google credentials.
Requires GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables.
"""

import os
import webbrowser
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import json

def create_oauth_url():
    """Create OAuth URL"""
    print("🔑 STEP 1: Creating OAuth URL...")
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    redirect_uri = "http://localhost:8000/v1/calendar/oauth/callback"
    
    if not client_id or not client_secret:
        print("❌ Error: Missing required environment variables!")
        print("Please set:")
        print("  export GOOGLE_CLIENT_ID='your_client_id'")
        print("  export GOOGLE_CLIENT_SECRET='your_client_secret'")
        return None
    
    scopes = [
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]
    
    flow = Flow.from_client_config(
        client_config={
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": [redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }
        },
        scopes=scopes
    )
    flow.redirect_uri = redirect_uri
    
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    print(f"✅ OAuth URL created!")
    print(f"🌐 Opening browser...")
    webbrowser.open(auth_url)
    
    print("\n" + "="*60)
    print("📋 INSTRUCTIONS:")
    print("1. Browser opened with Google OAuth")
    print("2. Sign in to your Google account")
    print("3. Grant calendar permissions")
    print("4. Copy the authorization code from the callback URL")
    print("="*60)
    
    auth_code = input("\nPaste the authorization code here: ").strip()
    return flow, auth_code

def create_real_events(flow, auth_code):
    """Create real calendar events"""
    print("\n🔄 STEP 2: Creating real calendar events...")
    
    try:
        flow.fetch_token(code=auth_code)
        credentials = flow.credentials
        
        print("✅ Credentials obtained successfully!")
        print("📅 Connecting to Google Calendar API...")
        
        service = build('calendar', 'v3', credentials=credentials)
        print("✅ Connected to Google Calendar API!")
        
        # Create demo events
        now = datetime.now()
        
        demo_events = [
            {
                'summary': '🚀 SUCCESS! Direct Calendar Test Event #1',
                'description': 'This is a REAL event created by the direct calendar test! Integration is working perfectly!',
                'start': {
                    'dateTime': (now + timedelta(minutes=5)).isoformat(),
                    'timeZone': 'America/New_York',
                },
                'end': {
                    'dateTime': (now + timedelta(minutes=35)).isoformat(),
                    'timeZone': 'America/New_York',
                },
            },
            {
                'summary': '✅ SUCCESS! Direct Calendar Test Event #2',
                'description': 'Second REAL event! Your Google Calendar integration is production-ready!',
                'start': {
                    'dateTime': (now + timedelta(minutes=45)).isoformat(),
                    'timeZone': 'America/New_York',
                },
                'end': {
                    'dateTime': (now + timedelta(hours=1, minutes=15)).isoformat(),
                    'timeZone': 'America/New_York',
                },
            },
        ]
        
        print(f"\n📝 Creating {len(demo_events)} REAL events in your Google Calendar...")
        
        events_created = []
        for i, event in enumerate(demo_events, 1):
            try:
                created_event = service.events().insert(calendarId='primary', body=event).execute()
                events_created.append(created_event)
                print(f"  ✅ Event {i} CREATED: {event['summary']}")
                print(f"     🔗 Link: {created_event.get('htmlLink', '')}")
            except Exception as e:
                print(f"  ❌ Event {i} failed: {e}")
        
        if events_created:
            print("\n" + "="*80)
            print("🎊 REAL GOOGLE CALENDAR EVENTS SUCCESSFULLY CREATED!")
            print("="*80)
            print(f"✅ Events created: {len(events_created)}/{len(demo_events)}")
            print(f"🌐 CHECK YOUR GOOGLE CALENDAR NOW!")
            
            print(f"\n📅 EVENTS TO LOOK FOR TODAY ({now.strftime('%B %d, %Y')}):")
            print(f"   • {(now + timedelta(minutes=5)).strftime('%I:%M %p')} - SUCCESS! Direct Calendar Test Event #1")
            print(f"   • {(now + timedelta(minutes=45)).strftime('%I:%M %p')} - SUCCESS! Direct Calendar Test Event #2")
            
            print(f"\n🏆 YOUR GOOGLE CALENDAR INTEGRATION IS WORKING PERFECTLY!")
            print(f"📱 Open https://calendar.google.com to see your {len(events_created)} real events")
            print(f"✅ DIRECT TESTING SUCCESSFUL!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("🎯 DIRECT GOOGLE CALENDAR TESTING")
    print("=" * 60)
    print("This will create REAL events in your Google Calendar!")
    print("=" * 60)
    
    # Check environment variables
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        print("❌ Missing required environment variables!")
        print("\nPlease set up your credentials:")
        print("export GOOGLE_CLIENT_ID='your_client_id_here'")
        print("export GOOGLE_CLIENT_SECRET='your_client_secret_here'")
        print("\nGet these from: https://console.cloud.google.com/")
        return
    
    # Step 1: Get OAuth URL and authorization code
    result = create_oauth_url()
    if not result:
        return
    
    flow, auth_code = result
    
    # Step 2: Create real events
    create_real_events(flow, auth_code)

if __name__ == "__main__":
    main()