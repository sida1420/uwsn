"""Two sequential variants per process; six paired processes in total."""
from pathlib import Path
import subprocess
import sys

seed,group=sys.argv[1:]
groups={'a':('deposit_2x','heuristic_half'),'b':('deposit_4x','heuristic_quarter')}
for name in groups[group]:
    subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('full_run.py')),name,seed],check=True)
