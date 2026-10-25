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


def process_snapshot():
    result={}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdecimal():continue
        try:
            raw=(entry/'stat').read_text();end=raw.rindex(')');fields=raw[end+2:].split()
            result[int(entry.name)]=dict(parent=int(fields[1]),name=raw[raw.index('(')+1:end],
                start=fields[19],ticks=int(fields[11])+int(fields[12]),
                rss=int(fields[21])*os.sysconf('SC_PAGE_SIZE'))
        except (OSError,ValueError,IndexError):continue
    return result


def project_processes(snapshot,server,clients):
    """Scope descendants to the selected server; locate Kitty via its clients."""
    selected={server:'tmux server',**{pid:'tmux client' for pid in clients}}
    changed=True
    while changed:
        changed=False
        for pid,record in snapshot.items():
            if pid not in selected and record['parent'] in selected:
                selected[pid]='session descendants';changed=True
    for client in clients:
        seen=set();pid=client
        while pid in snapshot and pid not in seen:
            seen.add(pid)
            if snapshot[pid]['name'].lower().startswith('kitty'):
                selected[pid]='Kitty';break
            pid=snapshot[pid]['parent']
    return {pid:role for pid,role in selected.items() if pid in snapshot}


def process_usage(before,after,old_scope,new_scope,elapsed):
    groups={}
    for pid,role in new_scope.items():
        group=groups.setdefault(role,dict(processes=0,cpu_percent_one_core=0,rss_mib=0))
        group['processes']+=1;group['rss_mib']+=after[pid]['rss']/2**20
        if pid in old_scope and before[pid]['start']==after[pid]['start']:
            group['cpu_percent_one_core']+=max(0,after[pid]['ticks']-before[pid]['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed*100
    for group in groups.values():
        for key in ('cpu_percent_one_core','rss_mib'):group[key]=round(group[key],2)
    return groups


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds',type=float,default=8)
    parser.add_argument('--frames',type=int,default=24)
    args=parser.parse_args()
    if not 1<=args.seconds<=60 or not 5<=args.frames<=120:parser.error('seconds 1..60, frames 5..120')
    raw=subprocess.run(['tmux','-L',SOCKET,'list-panes','-a','-F',
                        '#{pane_pid}|#{pane_title}'],check=True,capture_output=True,text=True).stdout
    panes=[(int(pid),title) for line in raw.splitlines()
           for pid,title in [line.split('|',1)] if pid.isdecimal()]
    server=int(subprocess.check_output(['tmux','-L',SOCKET,'display-message','-p','#{pid}'],text=True))
    clients=[int(pid) for pid in subprocess.check_output(['tmux','-L',SOCKET,'list-clients','-F','#{client_pid}'],text=True).split()]
    tree_before=process_snapshot();scope_before=project_processes(tree_before,server,clients)
    before={pid:counters(pid) for pid,_ in panes};started=time.monotonic()
    time.sleep(args.seconds);elapsed=time.monotonic()-started
    tree_after=process_snapshot();scope_after=project_processes(tree_after,server,clients)
    groups=process_usage(tree_before,tree_after,scope_before,scope_after,elapsed)
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
                          process_groups=groups,
                          total_cpu_percent_one_core=round(sum(g['cpu_percent_one_core'] for g in groups.values()),2),
                          summed_rss_mib=round(sum(g['rss_mib'] for g in groups.values()),2),
                          appeared_processes=len(scope_after.keys()-scope_before.keys()),
                          exited_processes=len(scope_before.keys()-scope_after.keys()),
                          collector_cpu=summary(samples),raster_cpu=rendering,
                          note='Groups include the selected server, its descendants, attached clients and their Kitty ancestor. Kitty may serve other windows. Summed RSS double-counts shared pages. CPU excludes processes that exit between snapshots and processes first seen at the end. Compositor/GPU/WSLg overhead is outside these totals; microbenchmarks are CPU time, not display FPS.'),indent=2))


if __name__=='__main__':main()
