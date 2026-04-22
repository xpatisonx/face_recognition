#!/usr/bin/env bash
set -euo pipefail

export MPLCONFIGDIR="${PWD}/.mplconfig"

./.venv/bin/python main.py
