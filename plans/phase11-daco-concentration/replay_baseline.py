"""Replay controls with saturation diagnostics; assert full trajectory equality."""
import json
import sys
import full_run as trial

trial.CONFIGS['baseline']=trial.BASE
sys.argv=[sys.argv[0],'baseline',sys.argv[1]]
trial.main()
seed=int(sys.argv[2])
fresh=json.loads((trial.FOLDER/'full'/f'baseline_{seed}.json').read_text())
old=json.loads((trial.ROOT/'plans/phase10-daco-vs-pheromone/full'/f'daco_{seed}.json').read_text())
assert fresh['completed_rounds']==old['completed_rounds']
assert fresh['residual']==old['residual']
for before,after in zip(old['records'],fresh['records']):
    assert all(after[key]==value for key,value in before.items())
print('PASS full baseline replay',seed,flush=True)
