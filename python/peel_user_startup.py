"""
This is run when Peel Capture starts. It reads an environment variable. The variable
contains a list of script paths, each of which is run.
"""

import os

import logging
_logger = logging.getLogger(__name__)

PEELSTARTUPVAR = 'PEELSTARTUP'
PEELSTARTUPVAR_DEFAULT = ""

def startup():
    """ Run startup scripts listed in PEELSTARTUP environment variable """
    startup_paths = os.environ.get(PEELSTARTUPVAR, PEELSTARTUPVAR_DEFAULT).split(';')
    for path in startup_paths:
        path = os.path.normpath(path)
        if not os.path.exists(path):
            if path: _logger.error(f"Peel Capture startup script missing: {path}")
            continue

        try:
            # Run the script in the global namespace
            exec(open(path).read(), globals())
        except Exception as e:
            _logger.error(f"Error running startup script: {path}", exc_info=True)
