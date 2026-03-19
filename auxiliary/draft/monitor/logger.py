import time
import signal
import sys
from monitor_core import SystemMonitor
import db

def signal_handler(sig, frame):
    print("\nStopping logger...")
    sys.exit(0)

def main():
    print("Starting System Monitor Logger...")
    
    # Initialize DB
    db.init_db()
    
    # Initialize Core Monitor
    monitor = SystemMonitor()
    
    # Register exit handler
    signal.signal(signal.SIGINT, signal_handler)
    
    print("Logger running. Press Ctrl+C to stop.")
    
    # Allow sensor threads to warm up
    time.sleep(1)
    
    while True:
        try:
            # Get stats
            stats = monitor.get_stats()
            
            # Log to DB
            db.log_stats(stats)
            
            # Print brief status
            print(f"Logged: CPU={stats['cpu']:.1f}% RAM={stats['ram']:.1f}% GPU={stats['gpu']}% Temp={stats['temp']}C")
            
            # Wait 5 seconds
            time.sleep(5)
            
        except Exception as e:
            print(f"Error logging stats: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()