#!/bin/bash
set -e

# Default to production Gunicorn server if no command is supplied
if [ "$#" -eq 0 ]; then
    set -- gunicorn config.wsgi.application --bind 0.0.0.0:8000 --workers 3
fi

# Execute the requested process; schema migrations run as a separate release step.
exec "$@"
