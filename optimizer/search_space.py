"""D-ACO independent search coordinates."""

SPACE = dict(alpha=(.25,3.,False), beta=(0.,1.5,False), gamma=(0.,1.,False),
             Q=(.1,60.,True), tau_max=(4.,32.,False),
             rho_min=(.05,.4,False), rho_max=(.4,.9,False),
             theta=(0.,1.,False), load_density_weight=(0.,1.,False), load_power=(1.,4.,False))
