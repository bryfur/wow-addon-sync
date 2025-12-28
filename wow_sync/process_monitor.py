import asyncio
import psutil
from pathlib import Path
from typing import Optional, Callable


class ProcessMonitor:
    WOW_PROCESS_PATTERNS = [
        'wow.exe',
        'wowclassic.exe',
        'wow-64.exe',
        'wowclassic-64.exe',
        'world of warcraft.exe',
    ]
    
    def __init__(self, on_start_callback: Optional[Callable] = None,
                 on_stop_callback: Optional[Callable] = None,
                 log_callback: Optional[Callable] = None):
        self.on_start = on_start_callback
        self.on_stop = on_stop_callback
        self.log = log_callback or print
        
        self._monitor_task = None
        self._tracked_pids = set()
        self._running = False
    
    def _is_wow_process(self, proc_name):
        proc_name_lower = proc_name.lower()
        # Exclude our own process
        if 'wowsync' in proc_name_lower:
            return False
        return any(pattern.lower() in proc_name_lower for pattern in self.WOW_PROCESS_PATTERNS)
    
    async def start(self):
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        self.log("Process monitor started")
    
    async def stop(self):
        if not self._running:
            return
        
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        self.log("Process monitor stopped")
    
    async def _monitor_loop(self):
        while self._running:
            try:
                current_pids = set()
                
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        proc_name = proc.info['name']
                        if self._is_wow_process(proc_name):
                            pid = proc.info['pid']
                            current_pids.add(pid)
                            
                            if pid not in self._tracked_pids:
                                self.log(f"WoW process started: {proc_name} (PID: {pid})")
                                self._tracked_pids.add(pid)
                                if self.on_start:
                                    self.on_start(proc_name, pid)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                stopped_pids = self._tracked_pids - current_pids
                for pid in stopped_pids:
                    self.log(f"WoW process stopped (PID: {pid})")
                    if self.on_stop:
                        self.on_stop(pid)
                
                self._tracked_pids = current_pids
                
            except Exception as e:
                self.log(f"Process monitor error: {e}")
            
            await asyncio.sleep(2)
