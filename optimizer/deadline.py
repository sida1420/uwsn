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
        if remaining<=0: return dict(stop_reason='deadline_exhausted',spent_seconds=spent)
        command=[sys.executable,'-B','-m','optimizer','_run','--study',str(folder)]
        if workers is not None: command+=['--workers',str(workers)]
        begin=time.monotonic();process=subprocess.Popen(command)
        hard_stop=False
        try:
            while process.poll() is None:
                elapsed=time.monotonic()-begin
                atomic(ledger_path,dict(spent_seconds=spent+elapsed,pid=process.pid))
                if elapsed>=remaining-min(cfg['shutdown_reserve_seconds'],remaining*.1): (folder/'STOP').touch()
                if elapsed>=remaining:
                    hard_stop=True
                    try:
                        children=psutil.Process(process.pid).children(recursive=True)
                        for child in children: child.kill()
                    except psutil.Error: pass
                    process.kill();break
                time.sleep(min(.5,max(.01,remaining-elapsed)))
            process.wait(timeout=2)
        except KeyboardInterrupt:
            (folder/'STOP').touch()
            try: process.wait(timeout=min(15,max(0,remaining-(time.monotonic()-begin))))
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
