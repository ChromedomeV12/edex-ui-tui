"""Unprivileged Linux/WSL metrics. No network requests, GeoIP or shell hooks."""
from pathlib import Path
import os
import platform
import time


class Metrics:
    def __init__(self, proc=Path('/proc')):
        self.proc = proc
        self.previous_cpu = {}
        self.previous_net = None
        self.history = []
        self.net_history = []
        self.sample_times = []
        self.previous_processes = {}
        self.previous_process_time = None

    def sample(self):
        cpus = []
        for line in (self.proc/'stat').read_text().splitlines():
            key, *values = line.split()
            if not key.startswith('cpu') or key == 'cpu':
                continue
            counts = list(map(int, values[:8]))
            total, idle = sum(counts), counts[3] + counts[4]
            old = self.previous_cpu.get(key)
            usage = max(0, min(100, 100*(1-(idle-old[1])/(total-old[0])))) if old and total>old[0] else None
            cpus.append(usage)
            self.previous_cpu[key] = (total, idle)
        mem = {key: int(value.split()[0])*1024 for key, value in
               (line.split(':', 1) for line in (self.proc/'meminfo').read_text().splitlines())}
        net = [0, 0]
        for line in (self.proc/'net/dev').read_text().splitlines()[2:]:
            name, values = line.split(':', 1)
            if name.strip() == 'lo':
                continue
            fields = list(map(int, values.split()))
            net[0] += fields[0]; net[1] += fields[8]
        now = time.monotonic()
        rates = [None, None]
        if self.previous_net:
            before, counts = self.previous_net
            rates = [max(0, (value-old)/(now-before)) for value, old in zip(net, counts)]
        self.previous_net = (now, net)
        self.history.append(cpus); self.history = self.history[-80:]
        self.net_history.append(rates); self.net_history = self.net_history[-80:]
        self.sample_times.append(now);self.sample_times=self.sample_times[-80:]
        return dict(cpus=cpus, memory=mem, network=rates, history=self.history,
                    sample_times=self.sample_times, sampled_at=now,
                    net_history=self.net_history, net_totals=net,
                    details=self.details(mem['MemTotal'],now),
                    uptime=float((self.proc/'uptime').read_text().split()[0]))

    def details(self,total,now):
        def read(path,default='--'):
            try:return Path(path).read_text().strip()
            except OSError:return default
        model='--';mhz=[]
        try:
            for line in (self.proc/'cpuinfo').read_text().splitlines():
                if line.startswith('model name'):model=line.split(':',1)[1].strip()
                if line.startswith('cpu MHz'):mhz.append(float(line.split(':',1)[1]))
        except OSError:pass
        processes=[];current={}
        hz=os.sysconf('SC_CLK_TCK') if hasattr(os,'sysconf') else 100
        page=os.sysconf('SC_PAGE_SIZE') if hasattr(os,'sysconf') else 4096
        for entry in self.proc.iterdir():
            if not entry.name.isdecimal():continue
            try:
                stat=(entry/'stat').read_text();start=stat.index('(');end=stat.rindex(')')
                fields=stat[end+2:].split();name=stat[start+1:end]
                count=int(fields[11])+int(fields[12]);pid=int(entry.name)
                # Include process start time so PID reuse cannot inherit CPU deltas.
                key=(pid,fields[19]);current[key]=count;before=self.previous_processes.get(key)
                cpu=None if before is None or self.previous_process_time is None else max(0,
                    (count-before)/hz/(now-self.previous_process_time)*100)
                processes.append(dict(pid=pid,name=name,cpu=cpu,memory=int(fields[21])*page/total*100))
            except (OSError,ValueError,IndexError):continue
        self.previous_processes=current;self.previous_process_time=now
        processes.sort(key=lambda p:(p['cpu'] or 0,p['memory']),reverse=True)
        interface='--';address='--';state='--'
        try:
            routes=(self.proc/'net/route').read_text().splitlines()[1:]
            interface=next(row.split()[0] for row in routes if row.split()[1]=='00000000')
            state=read('/sys/class/net/'+interface+'/operstate').upper()
            import socket,fcntl,struct
            with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
                raw=fcntl.ioctl(s.fileno(),0x8915,struct.pack('256s',interface.encode()[:15]))
                address=socket.inet_ntoa(raw[20:24])
        except (OSError,StopIteration,IndexError):pass
        batteries=list(Path('/sys/class/power_supply').glob('BAT*/status'))
        power=read(batteries[0]) if batteries else 'AC / N/A'
        temperatures=[]
        for p in Path('/sys/class/thermal').glob('thermal_zone*/temp'):
            try:temperatures.append(int(p.read_text())/1000)
            except (OSError,ValueError):pass
        return dict(model=model,mhz=mhz,processes=processes[:5],tasks=len(current),
                    manufacturer=read('/sys/class/dmi/id/sys_vendor'),
                    hardware=read('/sys/class/dmi/id/product_name'),system=platform.system(),
                    power=power,temperature=max(temperatures) if temperatures else None,
                    interface=interface,address=address,state=state)
