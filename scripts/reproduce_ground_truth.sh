#!/usr/bin/env bash
set -euo pipefail

# Compart Time-Machine Replay Protocol
# Verifies autonomous API maintenance against real historical ground truth.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${ROOT_DIR}/python:${PYTHONPATH:-}"

PYTHON="${PYTHON:-python3}"

echo "================================================================================"
echo "    COMPART AUTOPATCH: REAL-WORLD TIME-MACHINE REPLAY PROTOCOL"
echo "================================================================================"
echo "Reproducing verified historical migrations against real open-source software..."
echo "=== TIER 1: Component-Level AST Mutation & Safety Policy (10 Cases) ==="
$PYTHON -m compart.cli.main reproduce all

echo ""
echo "=== TIER 2: Full-Repo Git History Replay Protocol (3 Flagship Cases) ==="
$PYTHON -m compart.cli.main reproduce --git

echo ""
echo "All replay protocols successfully completed with verified zero blast radius."
echo "================================================================================"
