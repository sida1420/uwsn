"""Sequential full fitness trials for one seed."""
import sys
import full_run

seed = sys.argv[1]
for name in ('density_005','risk_control','density_010'):
    sys.argv = [full_run.__file__,seed,name]
    full_run.main()
