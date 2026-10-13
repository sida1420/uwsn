"""Outer deadline includes startup, controller, checkpoint flush and reporting."""
from pathlib import Path
import subprocess,sys,time
import psutil
from optimizer.storage import read,atomic,lock

def launch(folder,workers=None):
    folder=Path(folder).resolve()
    with lock(folder/'campaign-deadline.lock'):
        # A supervisor killed alone may leave its controller alive. Never start
        # another child or wait on that controller outside our own deadline.
        with lock(folder/'controller.lock'): pass
        cfg=read(folder/'config.json');ledger_path=folder/'deadline-ledger.json'
        state=read(folder/'state.json')
        ledger=read(ledger_path) if ledger_path.exists() else dict(spent_seconds=state['spent_wall'])
        spent=max(ledger['spent_seconds'],state['spent_wall']);remaining=cfg['budget_seconds']-spent
        unfinished=[k for k in state.get('drain_trials',[]) if state['jobs'].get(k,{}).get('status')=='paused']
        if remaining<=0 and not unfinished: return dict(stop_reason='deadline_exhausted',spent_seconds=spent)
        command=[sys.executable,'-B','-m','optimizer','_run','--study',str(folder)]
        if workers is not None: command+=['--workers',str(workers)]
        begin=time.monotonic();process=subprocess.Popen(command)
        hard_stop=False
        try:
            while process.poll() is None:
                elapsed=time.monotonic()-begin
                atomic(ledger_path,dict(spent_seconds=spent+elapsed,pid=process.pid))
                # The budget closes admission in the controller. It does not
                # interrupt active cohorts, including their remaining seeds.
                time.sleep(.5)
            process.wait(timeout=2)
        except KeyboardInterrupt:
            (folder/'STOP').touch()
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                try:
                    for child in psutil.Process(process.pid).children(recursive=True): child.kill()
                except psutil.Error: pass
                process.kill();process.wait()
        finally:
            elapsed=spent+time.monotonic()-begin
            atomic(ledger_path,dict(spent_seconds=elapsed,hard_stop=hard_stop))
            # Includes startup and reporting; no budget reset on resume.
            with lock(folder/'controller.lock'):
                state=read(folder/'state.json');state['spent_wall']=max(state['spent_wall'],elapsed)
                if hard_stop: state['stop_reason']='hard_deadline'
                atomic(folder/'state.json',state)
        return read(ledger_path)
