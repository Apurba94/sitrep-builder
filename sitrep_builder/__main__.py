"""Start the app: python -m sitrep_builder [data.db] [--port 8040]"""
import sys

from .fieldkit import main_cli
from .web import create_app

sys.exit(main_cli(create_app, "sitrep.db", 8040, sys.argv))
