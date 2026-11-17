"""Lite onedir entry. Verification only runs when explicitly requested."""
import sys
sys.dont_write_bytecode = True  # Alembic sources must not write into the onedir.
from ivad_app.core.demo_policy import install_runtime_guard
install_runtime_guard()
if '--lite-check' in sys.argv:
    from ivad_app.demo_check import run
    raise SystemExit(run(sys.argv[sys.argv.index('--lite-check') + 1]))
from ivad_app.__main__ import main
raise SystemExit(main())
