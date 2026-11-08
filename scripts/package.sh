#!/usr/bin/env bash
# Builds dist/skill-atlas.zip, the file to upload in the Claude app (Customize > Skills).
set -euo pipefail
cd "$(dirname "$0")/.."
rm -f dist/skill-atlas.zip
mkdir -p dist
(cd plugins/skill-atlas/skills && zip -rq ../../../dist/skill-atlas.zip skill-atlas -x '*/__pycache__/*' '*.DS_Store')
echo "dist/skill-atlas.zip"
