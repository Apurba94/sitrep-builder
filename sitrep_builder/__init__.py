"""SitRep Builder: situation reports from activity data."""
from . import core
from .web import create_app

__all__ = ["core", "create_app"]
