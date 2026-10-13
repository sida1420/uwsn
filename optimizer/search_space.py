"""D-ACO search coordinates and initial parameter anchors."""
from dataclasses import asdict, replace
from algorithms.clustering.d_aco.parameters import DACOParameters

SPACE = dict(alpha=(.25,3.,False), beta=(0.,1.5,False), gamma=(0.,1.,False),
             Q=(.1,60.,True), tau_max=(4.,32.,False),
             rho_min=(.05,.4,False), rho_max=(.4,.9,False),
             theta=(0.,1.,False), load_density_weight=(0.,1.,False), load_power=(1.,4.,False))

def anchors():
    base=DACOParameters()
    return [asdict(p) for p in (base,replace(base,beta=.225,gamma=.1),replace(base,beta=.45,gamma=.2),
        replace(base,Q=20.),replace(base,Q=30.),
        replace(base,beta=0.,theta=0.,load_density_weight=0.,load_power=1.),
        replace(base,gamma=0.,theta=.5,load_density_weight=.5,load_power=3.),
        replace(base,beta=0.,gamma=0.,theta=1.,load_density_weight=1.,load_power=4.))]

