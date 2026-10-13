"""Import completed baseline measurements only when native science is identical."""
import csv,gzip,time,shutil
from pathlib import Path
from optimizer.storage import read,atomic,digest,lock
from optimizer.reference import energy_prefix,from_runs
from optimizer.adapters import get
from optimizer.provenance import assert_campaign
from network import NetworkInstance

def import_reference(source,destination):
    start=time.monotonic();source=Path(source).resolve();destination=Path(destination).resolve()
    with lock(source/'controller.lock'),lock(destination/'controller.lock'):
        cfg=assert_campaign(destination);new_epoch=read(destination/'provenance.json')
        state=read(destination/'state.json')
        if state['jobs'] or state['spent_wall']: raise ValueError('Reference import requires an unstarted destination')
        old_cfg=read(source/'config.json');old_epoch=read(source/'provenance.json')
        outcome=read(source/'trials/reference/outcome.json')
        if outcome['status']!='complete': raise ValueError('Only complete reference cohorts can be imported')
        if old_epoch['map_sha']!=new_epoch['map_sha']: raise ValueError('Reference map differs')
        # Map-generation code is not executed by the simulator. Exact map bytes
        # still must match; all simulation/algorithm source hashes must match.
        native_sources=lambda e:{k:v for k,v in e['sources'].items() if k.replace('\\','/')!='src/map_gen.py'}
        if native_sources(old_epoch)!=native_sources(new_epoch): raise ValueError('Reference simulation sources differ')
        for key in ('python','versions'):
            if old_epoch[key]!=new_epoch[key]: raise ValueError(f'Reference {key} differs')
        for module in ('adapters.py','diagnostics.py'):
            old_hash=next(v for k,v in old_epoch['harness'].items() if Path(k.replace('\\','/')).name==module)
            new_hash=next(v for k,v in new_epoch['harness'].items() if Path(k.replace('\\','/')).name==module)
            if old_hash!=new_hash: raise ValueError(f'Reference native construction/observer differs: {module}')
        for key in ('training_seeds','horizon','adaptive_total_rounds'):
            if cfg[key]!=old_cfg[key]: raise ValueError(f'Reference {key} differs')
        if [r['seed'] for r in outcome['runs']]!=cfg['training_seeds']: raise ValueError('Wrong reference seed cohort')
        if any(k!='reference' for k in read(source/'state.json')['jobs']):
            raise ValueError('Import is restricted to campaigns with no tuning trials')
        nodes=NetworkInstance.from_pickle(cfg['map']).N;adapter=get('simple');runs=[]
        # Validate every input before writing any imported trajectory.
        for original in outcome['runs']:
            identity=original['identity'];seed=original['seed']
            if identity['epoch']!=old_epoch or identity['config']!=old_cfg or identity['kind']!='simple' or identity['seed']!=seed:
                raise ValueError('Reference identity mismatch')
            if identity['effective']!=adapter.effective_config({}) or identity['adapter_version']!=adapter.adapter_version:
                raise ValueError('Reference SimpleACO parameters/version differ')
            if identity['native_fitness_id']!=adapter.native_fitness_id: raise ValueError('Reference fitness differs')
            records_path=source/'trials/reference'/str(seed)/'rounds.csv.gz'
            with gzip.open(records_path,'rt',encoding='utf-8',newline='') as handle: records=list(csv.DictReader(handle))
            if len(records)!=original['completed_rounds'] or any(int(r['round'])!=i for i,r in enumerate(records,1)):
                raise ValueError('Incomplete reference records')
            curve=energy_prefix(records,nodes);K=cfg['energy_window']
            runs.append({**original,'identity':dict(epoch=new_epoch,config=cfg,requested={},effective=adapter.effective_config({}),
                         seed=seed,kind='simple',energy_window=K,adapter_version=adapter.adapter_version,native_fitness_id=adapter.native_fitness_id),
                         'initial_nodes':nodes,'all_alive_energy_prefix':curve,'energy_window':K,
                         'energy_status':'comparable' if len(curve)>=K else 'not_comparable',
                         'energy_K':curve[K-1] if len(curve)>=K else None})
        reference=from_runs(runs,cfg)
        old_state=read(source/'state.json');ledger_path=source/'deadline-ledger.json'
        spent=max(old_state['spent_wall'],read(ledger_path)['spent_seconds'] if ledger_path.exists() else 0.)
        for result in runs:
            target=destination/'trials/reference'/str(result['seed']);target.mkdir(parents=True)
            atomic(target/'metrics.json',result)
            shutil.copyfile(source/'trials/reference'/str(result['seed'])/'rounds.csv.gz',target/'rounds.csv.gz')
        atomic(destination/'trials/reference/outcome.json',dict(status='complete',runs=runs))
        reference['origin']='validated completed SimpleACO measurements from '+str(source)
        atomic(destination/'reference.json',reference)
        atomic(destination/'reference-import.json',dict(source=str(source),source_provenance_sha=digest(source/'provenance.json'),
               source_outcome_sha=digest(source/'trials/reference/outcome.json'),source_records_sha={str(r['seed']):digest(source/'trials/reference'/str(r['seed'])/'rounds.csv.gz') for r in runs},
               copied_checkpoints=False,copied_tuning_scores=False,carried_spent_seconds=spent,
               generator_source_excluded=True,map_bytes_exactly_matched=True))
        state.update(spent_wall=spent+time.monotonic()-start,stop_reason='ready_with_imported_reference',
                     jobs={'reference':dict(number='reference',kind='simple',parameters={},status='complete')})
        atomic(destination/'state.json',state);atomic(destination/'deadline-ledger.json',dict(spent_seconds=state['spent_wall']))
        return reference
