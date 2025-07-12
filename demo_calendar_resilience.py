#!/usr/bin/env python3
"""
Google Calendar Network Resilience Demo

This script demonstrates the robustness of the Google Calendar integration:
- Network interruption recovery
- Automatic retry with exponential backoff
- Rate limiting handling
- Connection timeout management
- OAuth token refresh on expiry
- Graceful degradation scenarios
"""

import asyncio
import aiohttp
import time
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class NetworkConditionSimulator:
    """Simulates various network conditions for testing"""
    
    def __init__(self):
        self.failure_rate = 0.0
        self.latency_ms = 0
        self.timeout_rate = 0.0
        
    def set_poor_network(self):
        """Simulate poor network conditions"""
        self.failure_rate = 0.3  # 30% failure rate
        self.latency_ms = 2000   # 2 second delays
        self.timeout_rate = 0.2  # 20% timeout rate
        
    def set_unstable_network(self):
        """Simulate unstable network"""
        self.failure_rate = 0.15  # 15% failure rate
        self.latency_ms = 500     # 500ms delays
        self.timeout_rate = 0.1   # 10% timeout rate
        
    def set_rate_limited_network(self):
        """Simulate rate-limited network"""
        self.failure_rate = 0.05  # 5% failure rate
        self.latency_ms = 100     # 100ms delays
        self.timeout_rate = 0.05  # 5% timeout rate
        
    def reset_network(self):
        """Reset to normal network conditions"""
        self.failure_rate = 0.0
        self.latency_ms = 0
        self.timeout_rate = 0.0
        
    async def apply_conditions(self):
        """Apply current network conditions"""
        # Simulate network latency
        if self.latency_ms > 0:
            delay = random.uniform(0, self.latency_ms / 1000)
            await asyncio.sleep(delay)
        
        # Simulate network failures
        if random.random() < self.failure_rate:
            raise aiohttp.ClientError("Simulated network failure")
        
        # Simulate timeouts
        if random.random() < self.timeout_rate:
            raise asyncio.TimeoutError("Simulated network timeout")


class ResilientCalendarClient:
    """Calendar client with built-in resilience features"""
    
    def __init__(self, base_url: str, simulator: NetworkConditionSimulator):
        self.base_url = base_url
        self.simulator = simulator
        self.session = None
        self.stats = {
            'total_attempts': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'retries_performed': 0,
            'rate_limits_hit': 0,
            'network_errors': 0,
            'timeout_errors': 0
        }
    
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=50,
            limit_per_host=20,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        # Configure shorter timeouts to test timeout handling
        timeout = aiohttp.ClientTimeout(
            total=10,    # 10 second total timeout
            connect=3,   # 3 second connect timeout
            sock_read=5  # 5 second read timeout
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'Content-Type': 'application/json'}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def make_resilient_request(
        self, 
        method: str, 
        endpoint: str, 
        max_retries: int = 3, 
        **kwargs
    ) -> Dict[str, Any]:
        """Make HTTP request with comprehensive retry logic"""
        
        url = f"{self.base_url}/v1/calendar{endpoint}"
        last_exception = None
        
        for attempt in range(max_retries + 1):
            self.stats['total_attempts'] += 1
            
            try:
                # Apply network conditions simulation
                await self.simulator.apply_conditions()
                
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 200:
                        self.stats['successful_requests'] += 1
                        return await response.json()
                    
                    elif response.status == 429:  # Rate limited
                        self.stats['rate_limits_hit'] += 1
                        retry_after = int(response.headers.get('Retry-After', 1))
                        
                        logger.warning(f"Rate limited, waiting {retry_after}s before retry {attempt + 1}")
                        await asyncio.sleep(retry_after)
                        
                        if attempt < max_retries:
                            self.stats['retries_performed'] += 1
                            continue
                    
                    elif response.status == 401:  # Unauthorized - token expired
                        logger.warning("Token expired, would refresh in real implementation")
                        # In real implementation, would refresh OAuth token here
                        if attempt < max_retries:
                            self.stats['retries_performed'] += 1
                            await asyncio.sleep(1)
                            continue
                    
                    elif response.status >= 500:  # Server errors - retry
                        error_text = await response.text()
                        logger.warning(f"Server error {response.status}: {error_text}")
                        
                        if attempt < max_retries:
                            self.stats['retries_performed'] += 1
                            backoff_time = (2 ** attempt) + random.uniform(0, 1)
                            await asyncio.sleep(backoff_time)
                            continue
                    
                    else:  # Client errors - don't retry
                        error_text = await response.text()
                        logger.error(f"Client error {response.status}: {error_text}")
                        break
            
            except asyncio.TimeoutError as e:
                self.stats['timeout_errors'] += 1
                last_exception = e
                logger.warning(f"Request timeout on attempt {attempt + 1}")
                
                if attempt < max_retries:
                    self.stats['retries_performed'] += 1
                    backoff_time = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(backoff_time)
                    continue
            
            except (aiohttp.ClientError, ConnectionError) as e:
                self.stats['network_errors'] += 1
                last_exception = e
                logger.warning(f"Network error on attempt {attempt + 1}: {e}")
                
                if attempt < max_retries:
                    self.stats['retries_performed'] += 1
                    backoff_time = (2 ** attempt) + random.uniform(0, 1)
                    await asyncio.sleep(backoff_time)
                    continue
            
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                break
        
        # All retries exhausted
        self.stats['failed_requests'] += 1
        return {
            "error": f"Request failed after {max_retries + 1} attempts",
            "last_exception": str(last_exception) if last_exception else "Unknown error"
        }
    
    async def create_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create calendar event with resilience"""
        return await self.make_resilient_request('POST', '/events', json=event_data)
    
    async def get_events(self) -> Dict[str, Any]:
        """Get calendar events with resilience"""
        return await self.make_resilient_request('GET', '/events')
    
    async def get_status(self) -> Dict[str, Any]:
        """Get calendar status with resilience"""
        return await self.make_resilient_request('GET', '/status')


class ResilienceTestSuite:
    """Comprehensive resilience testing suite"""
    
    def __init__(self, client: ResilientCalendarClient, simulator: NetworkConditionSimulator):
        self.client = client
        self.simulator = simulator
    
    async def test_normal_conditions(self) -> Dict[str, Any]:
        """Test under normal network conditions"""
        logger.info("🟢 Testing under NORMAL network conditions")
        
        self.simulator.reset_network()
        
        events = []
        for i in range(10):
            event_data = {
                "title": f"Normal Test Event {i+1}",
                "description": "Testing under normal network conditions",
                "start_time": (datetime.now() + timedelta(days=i+1, hours=10)).isoformat(),
                "duration_minutes": 30,
                "timezone": "UTC"
            }
            events.append(event_data)
        
        start_time = time.time()
        tasks = [self.client.create_event(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successful = sum(1 for r in results if isinstance(r, dict) and 'error' not in r)
        
        return {
            'test_name': 'Normal Conditions',
            'total_events': len(events),
            'successful_events': successful,
            'duration': end_time - start_time,
            'success_rate': successful / len(events) * 100
        }
    
    async def test_poor_network(self) -> Dict[str, Any]:
        """Test under poor network conditions"""
        logger.info("🔴 Testing under POOR network conditions (30% failure, 2s latency)")
        
        self.simulator.set_poor_network()
        
        events = []
        for i in range(15):
            event_data = {
                "title": f"Poor Network Test Event {i+1}",
                "description": "Testing resilience under poor network conditions",
                "start_time": (datetime.now() + timedelta(days=10+i, hours=14)).isoformat(),
                "duration_minutes": 45,
                "timezone": "UTC"
            }
            events.append(event_data)
        
        start_time = time.time()
        tasks = [self.client.create_event(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successful = sum(1 for r in results if isinstance(r, dict) and 'error' not in r)
        
        return {
            'test_name': 'Poor Network',
            'total_events': len(events),
            'successful_events': successful,
            'duration': end_time - start_time,
            'success_rate': successful / len(events) * 100
        }
    
    async def test_unstable_network(self) -> Dict[str, Any]:
        """Test under unstable network conditions"""
        logger.info("🟡 Testing under UNSTABLE network conditions (15% failure, 500ms latency)")
        
        self.simulator.set_unstable_network()
        
        events = []
        for i in range(20):
            event_data = {
                "title": f"Unstable Network Test {i+1}",
                "description": "Testing resilience under unstable network",
                "start_time": (datetime.now() + timedelta(days=20+i, hours=9)).isoformat(),
                "duration_minutes": 60,
                "timezone": "UTC"
            }
            events.append(event_data)
        
        start_time = time.time()
        tasks = [self.client.create_event(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.time()
        
        successful = sum(1 for r in results if isinstance(r, dict) and 'error' not in r)
        
        return {
            'test_name': 'Unstable Network',
            'total_events': len(events),
            'successful_events': successful,
            'duration': end_time - start_time,
            'success_rate': successful / len(events) * 100
        }
    
    async def test_rate_limiting_recovery(self) -> Dict[str, Any]:
        """Test rate limiting and recovery"""
        logger.info("⚡ Testing RATE LIMITING and recovery")
        
        self.simulator.set_rate_limited_network()
        
        # Create a burst of requests to trigger rate limiting
        events = []
        for i in range(25):
            event_data = {
                "title": f"Rate Limit Test {i+1}",
                "description": "Testing rate limiting recovery",
                "start_time": (datetime.now() + timedelta(days=40+i, hours=11)).isoformat(),
                "duration_minutes": 30,
                "timezone": "UTC"
            }
            events.append(event_data)
        
        start_time = time.time()
        
        # Send requests in rapid succession to trigger rate limiting
        tasks = [self.client.create_event(event) for event in events]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        
        successful = sum(1 for r in results if isinstance(r, dict) and 'error' not in r)
        
        return {
            'test_name': 'Rate Limiting Recovery',
            'total_events': len(events),
            'successful_events': successful,
            'duration': end_time - start_time,
            'success_rate': successful / len(events) * 100,
            'rate_limits_hit': self.client.stats['rate_limits_hit']
        }
    
    async def test_mixed_operations(self) -> Dict[str, Any]:
        """Test mixed operations under varying conditions"""
        logger.info("🔄 Testing MIXED operations with varying network conditions")
        
        results = []
        
        # Mix different operations: create events, get status, get events
        operations = []
        
        # Add event creation operations
        for i in range(5):
            event_data = {
                "title": f"Mixed Test Event {i+1}",
                "description": "Testing mixed operations",
                "start_time": (datetime.now() + timedelta(days=50+i, hours=13)).isoformat(),
                "duration_minutes": 45,
                "timezone": "UTC"
            }
            operations.append(('create_event', event_data))
        
        # Add status check operations
        for i in range(3):
            operations.append(('get_status', None))
        
        # Add get events operations
        for i in range(2):
            operations.append(('get_events', None))
        
        # Randomize operation order
        random.shuffle(operations)
        
        # Change network conditions mid-test
        self.simulator.reset_network()
        
        start_time = time.time()
        
        for i, (operation, data) in enumerate(operations):
            # Change network conditions partway through
            if i == len(operations) // 2:
                logger.info("🔄 Switching to unstable network mid-test")
                self.simulator.set_unstable_network()
            
            if operation == 'create_event':
                result = await self.client.create_event(data)
            elif operation == 'get_status':
                result = await self.client.get_status()
            elif operation == 'get_events':
                result = await self.client.get_events()
            
            results.append(result)
            
            # Small delay between operations
            await asyncio.sleep(0.1)
        
        end_time = time.time()
        
        successful = sum(1 for r in results if isinstance(r, dict) and 'error' not in r)
        
        return {
            'test_name': 'Mixed Operations',
            'total_operations': len(operations),
            'successful_operations': successful,
            'duration': end_time - start_time,
            'success_rate': successful / len(operations) * 100
        }


async def main():
    """Main resilience demo function"""
    logger.info("🛡️  GOOGLE CALENDAR RESILIENCE DEMO")
    logger.info("=" * 60)
    logger.info("Testing network resilience, retry logic, and error recovery")
    print()
    
    # Initialize components
    simulator = NetworkConditionSimulator()
    
    async with ResilientCalendarClient("http://localhost:8000", simulator) as client:
        test_suite = ResilienceTestSuite(client, simulator)
        
        # Run all resilience tests
        test_results = []
        
        # Test 1: Normal conditions baseline
        result1 = await test_suite.test_normal_conditions()
        test_results.append(result1)
        await asyncio.sleep(2)
        
        # Test 2: Poor network conditions
        result2 = await test_suite.test_poor_network()
        test_results.append(result2)
        await asyncio.sleep(2)
        
        # Test 3: Unstable network conditions
        result3 = await test_suite.test_unstable_network()
        test_results.append(result3)
        await asyncio.sleep(2)
        
        # Test 4: Rate limiting recovery
        result4 = await test_suite.test_rate_limiting_recovery()
        test_results.append(result4)
        await asyncio.sleep(2)
        
        # Test 5: Mixed operations
        result5 = await test_suite.test_mixed_operations()
        test_results.append(result5)
        
        # Print comprehensive results
        print("\n" + "="*80)
        print("📊 RESILIENCE TEST RESULTS SUMMARY")
        print("="*80)
        
        for result in test_results:
            print(f"\n🧪 {result['test_name']}:")
            print(f"   📊 Success Rate: {result['success_rate']:.1f}% ({result['successful_events' if 'successful_events' in result else 'successful_operations']}/{result['total_events' if 'total_events' in result else 'total_operations']})")
            print(f"   ⏱️  Duration: {result['duration']:.2f} seconds")
            
            if 'rate_limits_hit' in result:
                print(f"   ⚠️  Rate Limits: {result['rate_limits_hit']}")
        
        # Overall statistics
        print(f"\n📈 OVERALL STATISTICS:")
        print(f"   🔢 Total Requests: {client.stats['total_attempts']}")
        print(f"   ✅ Successful: {client.stats['successful_requests']}")
        print(f"   ❌ Failed: {client.stats['failed_requests']}")
        print(f"   🔄 Retries: {client.stats['retries_performed']}")
        print(f"   ⚠️  Rate Limits: {client.stats['rate_limits_hit']}")
        print(f"   🌐 Network Errors: {client.stats['network_errors']}")
        print(f"   ⏰ Timeouts: {client.stats['timeout_errors']}")
        
        success_rate = (client.stats['successful_requests'] / client.stats['total_attempts']) * 100 if client.stats['total_attempts'] > 0 else 0
        print(f"\n🎯 Overall Success Rate: {success_rate:.1f}%")
        
        # Resilience rating
        if success_rate > 90:
            rating = "🔥 EXCELLENT - Highly resilient"
        elif success_rate > 80:
            rating = "✅ GOOD - Well resilient"
        elif success_rate > 70:
            rating = "⚠️  FAIR - Moderately resilient"
        else:
            rating = "❌ POOR - Needs improvement"
        
        print(f"🏆 Resilience Rating: {rating}")
        print("="*80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()