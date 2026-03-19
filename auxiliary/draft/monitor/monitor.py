import time
from monitor_core import SystemMonitor

if __name__ == "__main__":
    monitor = SystemMonitor()
    print("Starting System Monitor... (Press Ctrl+C to stop)")
    try:
        while True:
            time.sleep(1)
            stats = monitor.get_stats()
            # Clear screen ANSI code
            print("\033[H\033[J")
            print("System Activity Monitor")
            print("-" * 40)
            print(f"CPU Usage: {stats['cpu']:.1f}%")
            print(f"GPU Usage: {stats['gpu']}%")
            print(f"Temperature: {stats['temp']}°C")
            print(f"RAM Usage: {stats['ram']:.1f}%")
            
            # Format speed helper
            def fmt(b): return f"{b/1024:.1f} KB/s" if b < 1024**2 else f"{b/1024**2:.1f} MB/s"
            
            print(f"Disk Read: {fmt(stats['disk']['read_speed'])}")
            print(f"Disk Write: {fmt(stats['disk']['write_speed'])}")
            print(f"Net Up: {fmt(stats['net']['up_speed'])}")
            print(f"Net Down: {fmt(stats['net']['down_speed'])}")
            print("-" * 40)
    except KeyboardInterrupt:
        monitor.close()
        print("\nStopped.")