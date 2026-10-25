"""Resize the existing tmux layout without replacing panes or shell processes."""
import math
import time


def reflow(run=None):
    from launch import tmux
    from workspaces import lock
    run=run or tmux
    with lock():
        shell=run('show-options','-qv','-t','edex','@edex-shell')
        if not shell:return False
        values=run('display-message','-p','-t',shell,
                   '#{window_width},#{window_height},#{window_zoomed_flag},#{client_cell_height}').split(',')
        width,height,zoomed,cell_height=(int(value or 0) for value in values)
        if zoomed or width<140 or height<40:return False
        raw=run('list-panes','-t',shell,'-F','#{pane_id}|#{pane_width}|#{pane_height}|#{pane_title}')
        panes={parts[0]:(parts[3],int(parts[1]),int(parts[2]))
               for line in raw.splitlines() for parts in [line.split('|',3)] if len(parts)==4}
        files=run('show-options','-qv','-t','edex','@edex-files')
        tabs=run('show-options','-qv','-t','edex','@edex-tabs')
        system=next((pane for pane,(title,_,_) in panes.items() if title=='System'),None)
        network=next((pane for pane,(title,_,_) in panes.items() if title=='Network-column'),None)
        keyboard=next((pane for pane,(title,_,_) in panes.items() if title=='Keyboard'),None)
        if not system or not network or files not in panes or tabs not in panes:return False
        changed=False
        def resize(pane,axis,size):
            nonlocal changed
            # Earlier mutations can resize siblings. Read their current size
            # rather than trusting the snapshot taken before the first change.
            field='pane_width' if axis=='x' else 'pane_height'
            current=int(run('display-message','-p','-t',pane,'#{'+field+'}'))
            if current!=size:
                run('resize-pane','-t',pane,'-'+axis,str(size));changed=True
        resize(files,'y',int(height*(.36 if keyboard else .30)))
        side=max(1,int(width*.17))
        resize(system,'x',side);resize(network,'x',side)
        if keyboard:resize(keyboard,'x',int(width*.62))
        cell_height=cell_height or 20
        tab_rows=max(2,math.ceil((19+height*cell_height*.011)/cell_height))
        resize(tabs,'y',tab_rows)
        padding=run('show-options','-qv','-t','edex','@edex-shell-padding')
        if padding in panes:resize(padding,'y',1)
        if changed:
            run('set-option','-t','edex','@edex-layout-revision',str(time.monotonic_ns()))
        return changed
