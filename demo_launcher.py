#!/usr/bin/env python3
"""
Quick Demo Launcher for Google Calendar Integration

This script provides easy access to both multi-platform and performance demos.
Choose which demo to run based on what you want to showcase.
"""

import sys
import subprocess
import argparse

def run_demo(demo_type, **kwargs):
    """Run the specified demo type"""
    
    if demo_type == "multi-platform":
        print("🌐 Launching Multi-Platform Demo...")
        print("   - Cross-platform calendar sync")
        print("   - Platform-specific event creation")
        print("   - Real-time synchronization")
        print()
        subprocess.run([sys.executable, "demo_calendar_comprehensive.py"])
        
    elif demo_type == "performance":
        print("⚡ Launching Performance Demo...")
        
        if kwargs.get('stress'):
            print("   - Running full stress test suite")
            print("   - 10, 50, 100, 250, 500 event tests")
            subprocess.run([sys.executable, "demo_calendar_performance.py", "--stress-suite"])
        else:
            events = kwargs.get('events', 100)
            batch_size = kwargs.get('batch_size', 20)
            concurrent = kwargs.get('concurrent', 10)
            
            print(f"   - Creating {events} events")
            print(f"   - Batch size: {batch_size}")
            print(f"   - Max concurrent: {concurrent}")
            
            subprocess.run([
                sys.executable, "demo_calendar_performance.py",
                "--events", str(events),
                "--batch-size", str(batch_size),
                "--concurrent", str(concurrent)
            ])
            
    elif demo_type == "resilience":
        print("🛡️ Launching Network Resilience Demo...")
        print("   - Network interruption recovery")
        print("   - Rate limiting handling")
        print("   - Retry logic demonstration")
        print()
        subprocess.run([sys.executable, "demo_calendar_resilience.py"])
        
    elif demo_type == "quick":
        print("🚀 Quick Demo - Small Performance Test")
        print("   - 10 events for quick demonstration")
        subprocess.run([
            sys.executable, "demo_calendar_performance.py",
            "--events", "10",
            "--batch-size", "5",
            "--concurrent", "3"
        ])
        
    else:
        print(f"❌ Unknown demo type: {demo_type}")
        print("Available demos: multi-platform, performance, resilience, quick")

def main():
    parser = argparse.ArgumentParser(description='Google Calendar Integration Demo Launcher')
    parser.add_argument('demo_type', 
                       choices=['multi-platform', 'performance', 'resilience', 'quick'],
                       help='Type of demo to run')
    
    # Performance demo options
    parser.add_argument('--stress', action='store_true', 
                       help='Run full stress test suite (performance demo only)')
    parser.add_argument('--events', type=int, default=100,
                       help='Number of events for performance demo (default: 100)')
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Batch size for performance demo (default: 20)')
    parser.add_argument('--concurrent', type=int, default=10,
                       help='Max concurrent requests (default: 10)')
    
    args = parser.parse_args()
    
    print("🎯 Google Calendar Integration Demo Launcher")
    print("=" * 50)
    
    # Pre-demo information
    print("\n📋 Prerequisites:")
    print("   ✅ Backend server running (usually localhost:8000)")
    print("   ✅ Google Calendar API configured")
    print("   ✅ Required Python packages installed")
    print()
    
    # Run the requested demo
    run_demo(
        args.demo_type,
        stress=args.stress,
        events=args.events,
        batch_size=args.batch_size,
        concurrent=args.concurrent
    )

if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("🎯 Google Calendar Integration Demo Launcher")
        print("=" * 50)
        print("\nAvailable demos:")
        print("  📱 multi-platform  - Cross-platform sync demonstration")
        print("  ⚡ performance     - Bulk event creation and speed testing")
        print("  🛡️  resilience     - Network resilience and error recovery")
        print("  🚀 quick          - Quick 10-event demo")
        print("\nExamples:")
        print("  python demo_launcher.py quick")
        print("  python demo_launcher.py performance --events 50")
        print("  python demo_launcher.py performance --stress")
        print("  python demo_launcher.py multi-platform")
        print("  python demo_launcher.py resilience")
        print("\nFor more options: python demo_launcher.py --help")
    else:
        main()