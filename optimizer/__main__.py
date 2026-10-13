import argparse,json
from pathlib import Path
from optimizer.engine import initialize,run
from optimizer.storage import read
from optimizer.reporting import report
from optimizer.audit import source_audit

def main():
    parser=argparse.ArgumentParser();subs=parser.add_subparsers(dest='command',required=True)
    p=subs.add_parser('init');p.add_argument('--config',required=True);p.add_argument('--study',required=True);p.add_argument('--legacy',required=True);p.add_argument('--reference-from')
    p=subs.add_parser('audit');p.add_argument('--output',required=True)
    for cmd in ('run','_run','status','stop','report'):
        p=subs.add_parser(cmd);p.add_argument('--study',required=True)
        if cmd in ('run','_run'): p.add_argument('--workers',type=int,choices=range(1,5))
    args=parser.parse_args()
    if args.command=='init':
        result=initialize(args.config,args.study,args.legacy)
        if args.reference_from:
            from optimizer.reference_cache import import_reference
            import_reference(args.reference_from,result)
    elif args.command=='audit': source_audit(args.output);result='Audit saved'
    elif args.command=='run':
        from optimizer.deadline import launch
        result=launch(args.study,args.workers)
    elif args.command=='_run': result=run(args.study,args.workers)
    elif args.command=='status': result=read(Path(args.study)/'state.json')
    elif args.command=='stop': (Path(args.study)/'STOP').touch();result='Stop requested'
    else: result=report(args.study)
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
