#!/usr/bin/env python3
"""
Google Calendar Performance Stress Test

This script focuses specifically on testing the performance limits:
- Bulk event creation (configurable from 10 to 1000+ events)
- Concurrent request handling
- Rate limiting behavior
- Memory usage under load
- Response time analysis
"""

import asyncio
import aiohttp
import time
import json
import psutil
import statistics
from datetime import datetime, timedelta
from typing import List, Dict, Any
import argparse
from dataclasses import dataclass

@dataclass
class PerformanceMetrics:
    """Container for performance metrics"""
    total_events: int = 0
    successful_events: int = 0
    failed_events: int = 0
    total_time: float = 0.0
    events_per_second: float = 0.0
    avg_response_time: float = 0.0
    min_response_time: float = 0.0
    max_response_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    rate_limited_requests: int = 0

class CalendarPerformanceTester:
    """High-performance calendar API tester"""
    
    def __init__(self, base_url: str = "http://localhost:8000", max_concurrent: int = 50):
        self.base_url = base_url
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.session = None
        self.response_times = []
        self.metrics = PerformanceMetrics()
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=200, 
            limit_per_host=100,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        timeout = aiohttp.ClientTimeout(total=60, connect=10)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Omi-Performance-Tester/1.0'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def create_single_event(self, event_data: Dict[str, Any], event_id: int) -> Dict[str, Any]:
        """Create a single event with performance tracking"""
        
        async with self.semaphore:  # Limit concurrent requests
            start_time = time.time()
            
            try:
                url = f"{self.base_url}/v1/calendar/events"
                
                async with self.session.post(url, json=event_data) as response:
                    end_time = time.time()
                    response_time = end_time - start_time
                    self.response_times.append(response_time)
                    
                    if response.status == 200:
                        self.metrics.successful_events += 1
                        result = await response.json()
                        return {
                            'event_id': event_id,
                            'status': 'success',
                            'response_time': response_time,
                            'result': result
                        }
                    elif response.status == 429:
                        self.metrics.rate_limited_requests += 1
                        retry_after = int(response.headers.get('Retry-After', 1))
                        await asyncio.sleep(retry_after)
                        # Retry once after rate limit
                        return await self.create_single_event(event_data, event_id)
                    else:
                        self.metrics.failed_events += 1
                        error_text = await response.text()
                        return {
                            'event_id': event_id,
                            'status': 'failed',
                            'response_time': response_time,
                            'error': f"HTTP {response.status}: {error_text}"
                        }
                        
            except Exception as e:
                end_time = time.time()
                response_time = end_time - start_time
                self.response_times.append(response_time)
                self.metrics.failed_events += 1
                
                return {
                    'event_id': event_id,
                    'status': 'error',
                    'response_time': response_time,
                    'error': str(e)
                }
    
    def generate_test_events(self, count: int) -> List[Dict[str, Any]]:
        """Generate test events optimized for performance testing"""
        
        events = []
        base_time = datetime.now() + timedelta(days=30)
        
        # Pre-generate random values for better performance
        event_types = ["Meeting", "Review", "Demo", "Planning", "Training"]
        durations = [30, 60, 90, 120]
        
        for i in range(count):
            # Distribute events across time to avoid conflicts
            event_time = base_time + timedelta(
                days=(i // 20),  # 20 events per day max
                hours=9 + (i % 8),  # Business hours 9-17
                minutes=(i % 4) * 15  # 15-minute intervals
            )
            
            events.append({
                "title": f"Perf Test {event_types[i % len(event_types)]} #{i+1:04d}",
                "description": f"Performance test event {i+1} of {count}",
                "start_time": event_time.isoformat(),
                "duration_minutes": durations[i % len(durations)],
                "timezone": "UTC"
            })
        
        return events
    
    async def run_performance_test(self, event_count: int, batch_size: int = 50) -> PerformanceMetrics:
        """Run comprehensive performance test"""
        
        print(f"🚀 Starting performance test: {event_count} events, batch size: {batch_size}")
        print(f"🔧 Max concurrent requests: {self.max_concurrent}")
        
        # Reset metrics
        self.metrics = PerformanceMetrics()
        self.response_times = []
        
        # Generate test data
        print("📝 Generating test events...")
        events = self.generate_test_events(event_count)
        self.metrics.total_events = len(events)
        
        # Monitor system resources
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Start performance test
        print(f"⚡ Creating {event_count} events...")
        start_time = time.time()
        
        # Create events in batches to control load
        total_batches = (len(events) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(events))
            batch_events = events[start_idx:end_idx]
            
            print(f"  📦 Batch {batch_num + 1}/{total_batches}: {len(batch_events)} events")
            
            # Create all events in this batch concurrently
            tasks = [
                self.create_single_event(event, start_idx + i) 
                for i, event in enumerate(batch_events)
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Brief pause between batches to avoid overwhelming the system
            if batch_num < total_batches - 1:
                await asyncio.sleep(0.1)
        
        end_time = time.time()
        
        # Calculate final metrics
        self.metrics.total_time = end_time - start_time
        self.metrics.events_per_second = self.metrics.successful_events / self.metrics.total_time if self.metrics.total_time > 0 else 0
        
        if self.response_times:
            self.metrics.avg_response_time = statistics.mean(self.response_times)
            self.metrics.min_response_time = min(self.response_times)
            self.metrics.max_response_time = max(self.response_times)
        
        # System resource usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        self.metrics.memory_usage_mb = final_memory - initial_memory
        self.metrics.cpu_percent = process.cpu_percent()
        
        return self.metrics
    
    def print_performance_report(self, metrics: PerformanceMetrics):
        """Print detailed performance report"""
        
        print("\n" + "="*60)
        print("📊 PERFORMANCE TEST RESULTS")
        print("="*60)
        
        # Event Creation Stats
        print(f"📅 Events Created:     {metrics.successful_events:,} / {metrics.total_events:,}")
        print(f"✅ Success Rate:       {(metrics.successful_events/metrics.total_events)*100:.1f}%")
        print(f"❌ Failed Events:      {metrics.failed_events:,}")
        print(f"⚠️  Rate Limited:      {metrics.rate_limited_requests:,}")
        
        # Performance Metrics
        print(f"\n⚡ Performance:")
        print(f"🕒 Total Time:         {metrics.total_time:.2f} seconds")
        print(f"📈 Events/Second:      {metrics.events_per_second:.2f}")
        print(f"⏱️  Avg Response Time:  {metrics.avg_response_time*1000:.1f}ms")
        print(f"🏃 Min Response Time:  {metrics.min_response_time*1000:.1f}ms")
        print(f"🐌 Max Response Time:  {metrics.max_response_time*1000:.1f}ms")
        
        # System Resources
        print(f"\n💻 System Resources:")
        print(f"🧠 Memory Used:        {metrics.memory_usage_mb:.1f} MB")
        print(f"⚙️  CPU Usage:          {metrics.cpu_percent:.1f}%")
        
        # Performance Rating
        if metrics.events_per_second > 50:
            rating = "🔥 EXCELLENT"
        elif metrics.events_per_second > 20:
            rating = "✅ GOOD"
        elif metrics.events_per_second > 10:
            rating = "⚠️  FAIR"
        else:
            rating = "❌ NEEDS IMPROVEMENT"
        
        print(f"\n🎯 Performance Rating: {rating}")
        print("="*60)


async def run_stress_test_suite():
    """Run a comprehensive stress test suite"""
    
    print("🎯 GOOGLE CALENDAR PERFORMANCE STRESS TEST SUITE")
    print("=" * 60)
    
    # Test configurations
    test_configs = [
        {"events": 10, "batch_size": 5, "name": "Warm-up Test"},
        {"events": 50, "batch_size": 10, "name": "Light Load Test"},
        {"events": 100, "batch_size": 20, "name": "Medium Load Test"},
        {"events": 250, "batch_size": 25, "name": "Heavy Load Test"},
        {"events": 500, "batch_size": 50, "name": "Stress Test"},
    ]
    
    results = []
    
    async with CalendarPerformanceTester(max_concurrent=50) as tester:
        for config in test_configs:
            print(f"\n🚀 Running {config['name']} ({config['events']} events)...")
            
            metrics = await tester.run_performance_test(
                event_count=config['events'],
                batch_size=config['batch_size']
            )
            
            tester.print_performance_report(metrics)
            results.append((config['name'], metrics))
            
            # Rest between tests
            print("😴 Resting 5 seconds before next test...")
            await asyncio.sleep(5)
    
    # Summary comparison
    print("\n" + "="*80)
    print("📈 STRESS TEST SUITE SUMMARY")
    print("="*80)
    
    for name, metrics in results:
        print(f"{name:20} | {metrics.successful_events:4d} events | {metrics.events_per_second:6.1f} events/sec | {metrics.avg_response_time*1000:6.1f}ms avg")
    
    print("="*80)


async def main():
    """Main function with command line arguments"""
    
    parser = argparse.ArgumentParser(description='Google Calendar Performance Tester')
    parser.add_argument('--events', type=int, default=100, help='Number of events to create (default: 100)')
    parser.add_argument('--batch-size', type=int, default=20, help='Batch size for event creation (default: 20)')
    parser.add_argument('--concurrent', type=int, default=50, help='Max concurrent requests (default: 50)')
    parser.add_argument('--stress-suite', action='store_true', help='Run comprehensive stress test suite')
    parser.add_argument('--url', default='http://localhost:8000', help='Backend URL (default: http://localhost:8000)')
    
    args = parser.parse_args()
    
    if args.stress_suite:
        await run_stress_test_suite()
    else:
        async with CalendarPerformanceTester(base_url=args.url, max_concurrent=args.concurrent) as tester:
            metrics = await tester.run_performance_test(
                event_count=args.events,
                batch_size=args.batch_size
            )
            tester.print_performance_report(metrics)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()