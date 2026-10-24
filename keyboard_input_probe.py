"""Interactive touch/input check: display bytes, never execute or save them.

Run in this project's active central shell while its keyboard pane is visible.
Ctrl-D exits and restores the terminal mode.
"""
import os
import sys
import termios
import tty


def main():
    if not sys.stdin.isatty():raise SystemExit('Run this probe in the active terminal pane')
    old=termios.tcgetattr(0)
    print('Keyboard input probe: taps are displayed, never executed or saved.')
    print('Try letters, Shift + a, Back, Enter and arrows. Ctrl-D exits.',flush=True)
    try:
        tty.setraw(0)
        while True:
            payload=os.read(0,4096)
            if not payload or b'\x04' in payload:break
            sys.stdout.write(repr(payload)+'\r\n');sys.stdout.flush()
    finally:
        termios.tcsetattr(0,termios.TCSADRAIN,old)
        print('\nInput probe stopped; normal shell restored.')


if __name__=='__main__':main()
