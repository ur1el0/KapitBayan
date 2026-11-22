#!/bin/bash
set -e

# Default to production ASGI server if no command is supplied
if [ "$#" -eq 0 ]; then
    set -- daphne -b 0.0.0.0 -p 8000 config.asgi:application
fi

# Execute the requested process; schema migrations run as a separate release step.
exec "$@"
