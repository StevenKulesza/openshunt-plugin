#!/bin/bash
# Offline custom-adapter and HTTP transport contract tests.
exec python3 "$(cd "$(dirname "$0")" && pwd)/transport_test.py"
