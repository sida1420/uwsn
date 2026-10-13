import argparse
import json
from pathlib import Path
import tempfile
import yaml
from optimizer import PACKAGE
from optimizer.controller import initialize,run,status
from optimizer.storage import read
from optimizer.report import generate

def main():
    parser=argparse.ArgumentParser(description='Bounded, resumable D-ACO parameter studies')
    subs=parser.add_subparsers(dest='command',required=True)
    p=subs.add_parser('init');p.add_argument('--config',required=True);p.add_argument('--study',required=True)
    for command in ('run','status','stop','report'):
        p=subs.add_parser(command);p.add_argument('--study',required=True)
    p=subs.add_parser('validate');p.add_argument('--study',required=True);p.add_argument('--output',required=True);p.add_argument('--top',type=int,default=3)
    args=parser.parse_args()
    if args.command=='init': result=initialize(args.config,args.study)
    elif args.command=='run': result=run(args.study)
    elif args.command=='status': result=status(args.study)
    elif args.command=='report': result=generate(args.study)
    elif args.command=='stop':
        folder=Path(args.study).resolve();read(folder/'config.json');(folder/'STOP').touch();result={'graceful_stop_requested':str(folder)}
    else:
        if args.top<1: parser.error('--top must be positive')
        source=Path(args.study).resolve();cfg=read(source/'config.json')
        if cfg['mode']!='scientific' or cfg['study_role']!='training': raise ValueError('Validation needs a scientific training study')
        state=read(source/'state.json');feasible=[]
        for key,job in state['jobs'].items():
            path=source/'trials'/key/'aggregate.json'
            if path.exists() and read(path)['feasible']: feasible.append((read(path)['mean_service_capped'],job))
        selected=sorted(feasible,key=lambda x:x[0],reverse=True)[:args.top]
        if not selected: raise ValueError('No complete feasible training candidates')
        if (source/'validation-study.json').exists():
            raise ValueError('A validation study is already linked. Resume that study to preserve the combined eight-hour budget.')
        cfg.update(study_role='validation',training_seeds=cfg['validation_seeds'],validation_seeds=cfg['training_seeds'],
                   max_trials=len(selected),max_wall_hours=2.,max_session_hours=min(2.,cfg['max_session_hours']),reuse_history=False,sampler='random')
        with tempfile.TemporaryDirectory(dir=PACKAGE) as tmp:
            path=Path(tmp)/'config.yaml';path.write_text(yaml.safe_dump(cfg),encoding='utf-8')
            result=initialize(path,args.output)
        from optimizer.storage import atomic,digest
        atomic(Path(args.output)/'shortlist.json',dict(training_study=str(source),
            training_trials=[job['number'] for _,job in selected],parameters=[job['parameters'] for _,job in selected]))
        atomic(Path(args.output)/'shortlist-hash.json',dict(sha256=digest(Path(args.output)/'shortlist.json')))
        atomic(source/'validation-study.json',dict(study=str(Path(args.output).resolve()),max_wall_hours=2.))
        result['note']='Frozen validation study initialized only; run explicitly to evaluate it'
    print(json.dumps(result,indent=2,allow_nan=False))

if __name__=='__main__': main()
