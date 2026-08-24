#!/usr/bin/env bash
set -euo pipefail

if ! command -v hugo >/dev/null 2>&1; then
  echo "Hugo não está instalado. Veja: https://gohugo.io/installation/" >&2
  exit 1
fi

hugo server --noHTTPCache
