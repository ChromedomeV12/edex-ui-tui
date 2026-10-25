"""Read-only profiling of this project, with no renderer restarts or input injection."""
import argparse
import json
import os
from pathlib import Path
import statistics
import subprocess
import time
import zlib
from metrics import Metrics
from columns import render_column
from launch import SOCKET


def summary(values):
    values=sorted(values)
    return dict(median_ms=round(statistics.median(values)*1000,3),
                p95_ms=round(values[min(len(values)-1,int(len(values)*.95))]*1000,3))


def counters(pid):
    try:
        row=(Path('/proc')/str(pid)/'stat').read_text().rsplit(')',1)[1].split()
        return int(row[11])+int(row[12]),int(row[21])*os.sysconf('SC_PAGE_SIZE')
    except (OSError,ValueError,IndexError):return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=8)
    parser.add_argument('--frames',type=int,default=24)
    args=parser.parse_args()
    if not 1<=args.seconds<=60 or not 5<=args.frames<=120:parser.error('seconds 1..60, frames 5..120')
    raw=subprocess.run(['tmux','-L',SOCKET,'list-panes','-a','-F',
                        '#{pane_pid}|#{pane_title}'],check=True,capture_output=True,text=True).stdout
    panes=[(int(line.split('|',1)[0]),line.split('|',1)[1]) for line in raw.splitlines()]
    before={pid:counters(pid) for pid,_ in panes};started=time.monotonic()
    time.sleep(args.seconds);elapsed=time.monotonic()-started
    usage=[]
    for pid,title in panes:
        old=before[pid];new=counters(pid)
        if old and new:
            usage.append(dict(pane=title,cpu_percent_one_core=round((new[0]-old[0])/os.sysconf('SC_CLK_TCK')/elapsed*100,2),
                              rss_mib=round(new[1]/2**20,2)))
    metrics=Metrics();samples=[]
    for _ in range(12):
        start=time.process_time();data=metrics.sample();samples.append(time.process_time()-start)
    rendering={}
    for kind,width,height in [('system',396,640),('network-column',360,640)]:
        timings={};sizes={}
        for encoding in ('png','zlib-rgb'):
            times=[];lengths=[]
            for frame in range(args.frames):
                start=time.process_time()
                image=render_column(kind,width,height,data,10+frame/24,raster=encoding!='png')
                payload=zlib.compress(image.tobytes(),1) if encoding!='png' else image
                times.append(time.process_time()-start);lengths.append(len(payload))
            timings[encoding]=summary(times);sizes[encoding]=round(statistics.mean(lengths))
        rendering[kind]=dict(cpu=timings,mean_payload_bytes=sizes)
    print(json.dumps(dict(interval_seconds=round(elapsed,2),pane_processes=usage,
                          collector_cpu=summary(samples),raster_cpu=rendering,
                          note='Pane CPU excludes descendants/Kitty/tmux. Microbenchmarks use CPU time, warmed fonts and fixed geometry; not display FPS.'),indent=2))


if __name__=='__main__':main()
