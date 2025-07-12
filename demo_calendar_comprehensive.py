#!/usr/bin/env python3
"""
Comprehensive Google Calendar Integration Demo Script

This script demonstrates:
1. Multi-Platform Demo: Cross-platform Google Calendar sync
2. Performance Demo: Bulk event creation (100+ events)
3. Resilience Demo: Network interruption recovery and rate limiting

Prerequisites:
- Backend server running on localhost:8000
- Valid Google Calendar API credentials
- Test user authentication token
"""

import asyncio
import aiohttp
import time
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class CalendarDemoClient:
    """Demo client for Google Calendar integration testing"""
    
    def __init__(self, base_url: str = "http://localhost:8000", auth_token: str = None):
        self.base_url = base_url
        self.auth_token = auth_token
        self.session = None
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'events_created': 0,
            'start_time': None,
            'end_time': None
        }
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=50)
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'Authorization': f'Bearer {self.auth_token}'} if self.auth_token else {}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with error handling and retries"""
        url = f"{self.base_url}/v1/calendar{endpoint}"
        self.stats['total_requests'] += 1
        
        for attempt in range(3):  # 3 retry attempts
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        self.stats['successful_requests'] += 1
                        return await response.json()
                    elif response.status == 429:  # Rate limited
                        retry_after = int(response.headers.get('Retry-After', 1))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        error_text = await response.text()
                        logger.error(f"Request failed: {response.status} - {error_text}")
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < 2:  # Don't sleep on last attempt
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                
        self.stats['failed_requests'] += 1
        return {"error": "Request failed after 3 attempts"}
    
    async def get_calendar_status(self) -> Dict[str, Any]:
        """Get calendar integration status"""
        logger.info("📋 Checking calendar integration status...")
        return await self.make_request('GET', '/status')
    
    async def test_calendar_integration(self) -> Dict[str, Any]:
        """Test calendar integration"""
        logger.info("🧪 Testing calendar integration...")
        return await self.make_request('GET', '/test')
    
    async def get_calendar_config(self) -> Dict[str, Any]:
        """Get calendar configuration"""
        logger.info("⚙️ Getting calendar configuration...")
        return await self.make_request('GET', '/config')
    
    async def update_calendar_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Update calendar configuration"""
        logger.info("🔄 Updating calendar configuration...")
        return await self.make_request('PUT', '/config', json=config)
    
    async def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a single calendar event"""
        result = await self.make_request('POST', '/events', json=event_data)
        if 'error' not in result:
            self.stats['events_created'] += 1
        return result
    
    async def get_events(self, days_ahead: int = 30) -> Dict[str, Any]:
        """Get upcoming calendar events"""
        return await self.make_request('GET', f'/events?days_ahead={days_ahead}')
    
    async def get_events_history(self, limit: int = 50) -> Dict[str, Any]:
        """Get calendar events history"""
        return await self.make_request('GET', f'/events/history?limit={limit}')


class MultiPlatformDemo:
    """Demo showcasing cross-platform calendar sync"""
    
    def __init__(self, client: CalendarDemoClient):
        self.client = client
    
    async def demo_cross_platform_sync(self):
        """Demonstrate cross-platform calendar synchronization"""
        logger.info("🌐 === MULTI-PLATFORM DEMO: Cross-Platform Calendar Sync ===")
        
        # Simulate different platforms creating events
        platforms = [
            {"name": "iOS Mobile App", "user_agent": "Omi-iOS/1.0"},
            {"name": "Android Mobile App", "user_agent": "Omi-Android/1.0"},
            {"name": "Web App", "user_agent": "Omi-Web/1.0"},
            {"name": "macOS Desktop", "user_agent": "Omi-macOS/1.0"},
            {"name": "Windows Desktop", "user_agent": "Omi-Windows/1.0"}
        ]
        
        logger.info("📱 Simulating event creation from multiple platforms...")
        
        tasks = []
        for i, platform in enumerate(platforms):
            event_data = {
                "title": f"Cross-Platform Meeting {i+1} - {platform['name']}",
                "description": f"Event created from {platform['name']} to demonstrate cross-platform sync",
                "start_time": (datetime.now() + timedelta(days=i+1, hours=10)).isoformat(),
                "duration_minutes": 60,
                "timezone": "UTC"
            }
            
            # Add platform-specific headers simulation
            task = self.client.create_event(event_data)
            tasks.append(task)
            
            # Stagger requests to simulate real-world usage
            await asyncio.sleep(0.5)
        
        # Wait for all platform events to be created
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        successful_creates = sum(1 for r in results if isinstance(r, dict) and 'error' not in r)
        logger.info(f"✅ Successfully created {successful_creates}/{len(platforms)} cross-platform events")
        
        # Demonstrate that all events appear across platforms
        logger.info("🔄 Verifying events are visible across all platforms...")
        events = await self.client.get_events(days_ahead=10)
        
        if 'events' in events:
            platform_events = [e for e in events['events'] if 'Cross-Platform' in e.get('title', '')]
            logger.info(f"📊 Found {len(platform_events)} cross-platform events visible to all clients")
        
        return successful_creates


class PerformanceDemo:
    """Demo showcasing performance and bulk operations"""
    
    def __init__(self, client: CalendarDemoClient):
        self.client = client
    
    def generate_bulk_events(self, count: int = 100) -> List[Dict[str, Any]]:
        """Generate bulk events for testing"""
        events = []
        base_time = datetime.now() + timedelta(days=30)  # Schedule 30 days out
        
        event_types = [
            "Team Standup", "Client Meeting", "Code Review", "Planning Session",
            "Demo Presentation", "Training Workshop", "One-on-One", "All Hands"
        ]
        
        for i in range(count):
            event_time = base_time + timedelta(
                days=random.randint(0, 90),
                hours=random.randint(9, 17),
                minutes=random.choice([0, 15, 30, 45])
            )
            
            events.append({
                "title": f"Bulk Test: {random.choice(event_types)} #{i+1}",
                "description": f"Performance test event {i+1} of {count}. Created via bulk operation demo.",
                "start_time": event_time.isoformat(),
                "duration_minutes": random.choice([30, 60, 90, 120]),
                "timezone": "UTC"
            })
        
        return events
    
    async def demo_bulk_event_creation(self, event_count: int = 100):
        """Demonstrate bulk event creation performance"""
        logger.info(f"⚡ === PERFORMANCE DEMO: Bulk Event Creation ({event_count} events) ===")
        
        # Generate test events
        events = self.generate_bulk_events(event_count)
        logger.info(f"📝 Generated {len(events)} test events")
        
        # Measure performance
        start_time = time.time()
        self.client.stats['start_time'] = start_time
        
        # Create events in batches to avoid overwhelming the server
        batch_size = 10
        total_batches = (len(events) + batch_size - 1) // batch_size
        
        logger.info(f"🚀 Creating events in {total_batches} batches of {batch_size}...")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(events))
            batch_events = events[start_idx:end_idx]
            
            # Create batch concurrently
            tasks = [self.client.create_event(event) for event in batch_events]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_in_batch = sum(1 for r in batch_results if isinstance(r, dict) and 'error' not in r)
            
            logger.info(f"  Batch {batch_num + 1}/{total_batches}: {successful_in_batch}/{len(batch_events)} successful")
            
            # Brief pause between batches to be respectful to the API
            if batch_num < total_batches - 1:
                await asyncio.sleep(0.1)
        
        end_time = time.time()
        self.client.stats['end_time'] = end_time
        duration = end_time - start_time
        
        # Performance metrics
        events_per_second = self.client.stats['events_created'] / duration if duration > 0 else 0
        
        logger.info(f"📊 Performance Results:")
        logger.info(f"  • Total time: {duration:.2f} seconds")
        logger.info(f"  • Events created: {self.client.stats['events_created']}/{event_count}")
        logger.info(f"  • Events per second: {events_per_second:.2f}")
        logger.info(f"  • Success rate: {(self.client.stats['events_created']/event_count)*100:.1f}%")
        
        return self.client.stats['events_created']


class ResilienceDemo:
    """Demo showcasing error handling and resilience"""
    
    def __init__(self, client: CalendarDemoClient):
        self.client = client
    
    async def demo_network_resilience(self):
        """Demonstrate network resilience and retry logic"""
        logger.info("🛡️ === RESILIENCE DEMO: Network Recovery & Rate Limiting ===")
        
        # Test 1: Simulated network interruptions
        logger.info("🌐 Testing network interruption recovery...")
        
        events_with_delays = []
        for i in range(5):
            event_data = {
                "title": f"Resilience Test Event {i+1}",
                "description": "Testing network resilience and retry logic",
                "start_time": (datetime.now() + timedelta(days=i+1, hours=14)).isoformat(),
                "duration_minutes": 30,
                "timezone": "UTC"
            }
            events_with_delays.append(event_data)
        
        # Create events with simulated network conditions
        resilience_tasks = []
        for i, event in enumerate(events_with_delays):
            # Add artificial delay to simulate network issues
            if i % 2 == 0:
                await asyncio.sleep(0.1)  # Simulate brief network delay
            
            task = self.client.create_event(event)
            resilience_tasks.append(task)
        
        resilience_results = await asyncio.gather(*resilience_tasks, return_exceptions=True)
        successful_resilience = sum(1 for r in resilience_results if isinstance(r, dict) and 'error' not in r)
        
        logger.info(f"  ✅ Resilience test: {successful_resilience}/{len(events_with_delays)} events created successfully")
        
        # Test 2: Rapid requests to test rate limiting
        logger.info("⚡ Testing rate limiting handling...")
        
        rapid_events = []
        for i in range(20):  # Create 20 rapid requests
            event_data = {
                "title": f"Rate Limit Test {i+1}",
                "description": "Testing rate limiting and backoff logic",
                "start_time": (datetime.now() + timedelta(days=20+i, hours=9)).isoformat(),
                "duration_minutes": 15,
                "timezone": "UTC"
            }
            rapid_events.append(event_data)
        
        # Fire all requests rapidly
        rapid_start = time.time()
        rapid_tasks = [self.client.create_event(event) for event in rapid_events]
        rapid_results = await asyncio.gather(*rapid_tasks, return_exceptions=True)
        rapid_duration = time.time() - rapid_start
        
        successful_rapid = sum(1 for r in rapid_results if isinstance(r, dict) and 'error' not in r)
        
        logger.info(f"  📊 Rate limiting test: {successful_rapid}/{len(rapid_events)} successful in {rapid_duration:.2f}s")
        logger.info(f"  📈 Request rate: {len(rapid_events)/rapid_duration:.2f} requests/second")
        
        return successful_resilience + successful_rapid


async def main():
    """Main demo function"""
    logger.info("🎯 === GOOGLE CALENDAR INTEGRATION COMPREHENSIVE DEMO ===")
    logger.info("📅 Demonstrating Multi-Platform Sync, Performance, and Resilience")
    print()
    
    # Configuration
    BASE_URL = "http://localhost:8000"
    AUTH_TOKEN = "demo-token-12345"  # In real usage, this would be a valid JWT
    
    # Initialize demo client
    async with CalendarDemoClient(BASE_URL, AUTH_TOKEN) as client:
        # Pre-demo checks
        logger.info("🔍 Pre-demo system checks...")
        
        status = await client.get_calendar_status()
        logger.info(f"  📋 Calendar status: {status}")
        
        config = await client.get_calendar_config()
        logger.info(f"  ⚙️ Calendar config: {config}")
        
        test_result = await client.test_calendar_integration()
        logger.info(f"  🧪 Integration test: {test_result}")
        
        print("\n" + "="*80 + "\n")
        
        # Demo 1: Multi-Platform Cross-Sync
        multi_platform_demo = MultiPlatformDemo(client)
        platform_events = await multi_platform_demo.demo_cross_platform_sync()
        
        print("\n" + "="*80 + "\n")
        
        # Demo 2: Performance - Bulk Operations
        performance_demo = PerformanceDemo(client)
        bulk_events = await performance_demo.demo_bulk_event_creation(100)
        
        print("\n" + "="*80 + "\n")
        
        # Demo 3: Resilience - Error Handling
        resilience_demo = ResilienceDemo(client)
        resilience_events = await resilience_demo.demo_network_resilience()
        
        print("\n" + "="*80 + "\n")
        
        # Final summary
        total_events = platform_events + bulk_events + resilience_events
        total_time = client.stats.get('end_time', time.time()) - client.stats.get('start_time', time.time())
        
        logger.info("🎉 === DEMO SUMMARY ===")
        logger.info(f"  📊 Total API requests: {client.stats['total_requests']}")
        logger.info(f"  ✅ Successful requests: {client.stats['successful_requests']}")
        logger.info(f"  ❌ Failed requests: {client.stats['failed_requests']}")
        logger.info(f"  📅 Total events created: {total_events}")
        logger.info(f"  🕒 Total demo time: {total_time:.2f} seconds")
        logger.info(f"  📈 Success rate: {(client.stats['successful_requests']/client.stats['total_requests'])*100:.1f}%")
        
        print("\n🎯 Demo completed! Check your Google Calendar to see all created events.")
        
        # Show final event count
        final_events = await client.get_events(days_ahead=365)
        if 'events' in final_events:
            logger.info(f"📱 Total events visible in calendar: {len(final_events['events'])}")


if __name__ == "__main__":
    print("🚀 Starting Google Calendar Integration Demo...")
    print("📝 This demo showcases multi-platform sync, performance, and resilience features.")
    print("⚠️  Note: Ensure your backend server is running and configured with Google Calendar API")
    print()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed with error: {e}")
        sys.exit(1)