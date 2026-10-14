"""Windows distribution entry, with an explicit developer deployment check."""
import sys
if '--deployment-check' in sys.argv:
    from ivad_app.distribution_check import run
    raise SystemExit(run(sys.argv[sys.argv.index('--deployment-check')+1]))
from ivad_app.__main__ import main
raise SystemExit(main())
