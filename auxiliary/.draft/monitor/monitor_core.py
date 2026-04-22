import psutil
import subprocess
import time
import re
import threading

class SystemMonitor:
    def __init__(self):
        self.last_net_io = psutil.net_io_counters()
        self.last_disk_io = psutil.disk_io_counters()
        self.last_time = time.time()
        
        # Shared state for background updates
        self.gpu_usage = 0
        self.temperature = 0
        self.running = True
        
        # Start background thread for slow operations (tegrastats)
        self.thread = threading.Thread(target=self._update_tegrastats_loop, daemon=True)
        self.thread.start()

    def _update_tegrastats_loop(self):
        """Background loop to fetch tegrastats persistently."""
        try:
            # Start tegrastats process with 1s interval
            proc = subprocess.Popen(['tegrastats', '--interval', '1000'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  text=True,
                                  bufsize=1) # Line buffered
            
            self.tegra_proc = proc
            
            while self.running and proc.poll() is None:
                line = proc.stdout.readline()
                if not line:
                    break
                    
                # Parse GPU
                gpu_match = re.search(r'GR3D_FREQ (\d+)%', line)
                if gpu_match:
                    self.gpu_usage = int(gpu_match.group(1))
                
                # Parse Temp
                temp_match = re.search(r'cpu@([\d.]+)C', line)
                if temp_match:
                    self.temperature = float(temp_match.group(1))
                    
        except Exception as e:
            # print(f"Error in tegrastats loop: {e}")
            pass
        finally:
            if hasattr(self, 'tegra_proc'):
                self.tegra_proc.terminate()

    def get_stats(self):
        """Get current system stats with calculated rates."""
        current_time = time.time()
        elapsed = current_time - self.last_time
        
        # Prevent division by zero if called too fast
        if elapsed < 0.1:
            elapsed = 0.1

        # CPU (non-blocking if interval=None)
        cpu = psutil.cpu_percent(interval=None)
        
        # RAM
        ram = psutil.virtual_memory().percent
        
        # Disk I/O Rates
        disk_io = psutil.disk_io_counters()
        read_speed = (disk_io.read_bytes - self.last_disk_io.read_bytes) / elapsed
        write_speed = (disk_io.write_bytes - self.last_disk_io.write_bytes) / elapsed
        
        # Network I/O Rates
        net_io = psutil.net_io_counters()
        up_speed = (net_io.bytes_sent - self.last_net_io.bytes_sent) / elapsed
        down_speed = (net_io.bytes_recv - self.last_net_io.bytes_recv) / elapsed
        
        # Update state
        self.last_disk_io = disk_io
        self.last_net_io = net_io
        self.last_time = current_time
        
        return {
            'cpu': cpu,
            'gpu': self.gpu_usage,
            'temp': self.temperature,
            'ram': ram,
            'disk': {
                'read_speed': read_speed,
                'write_speed': write_speed
            },
            'net': {
                'up_speed': up_speed,
                'down_speed': down_speed
            }
        }
    
    def close(self):
        self.running = False
        if self.thread.is_alive():
            self.thread.join(timeout=1.0)
