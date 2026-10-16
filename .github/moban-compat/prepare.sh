#!/usr/bin/env bash
set -euo pipefail

compat="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
build="$(mktemp -d)"
trap 'rm -rf -- "$build"' EXIT
export SOURCE_DATE_EPOCH=315532800
mkdir "$build/wheels"

python -m pip install --only-binary=:all: --require-hashes -r "$compat/bootstrap.txt"
python -m pip download --no-deps --only-binary=:all: --require-hashes \
  -r "$compat/upstream.txt" -d "$build/original"
python -m wheel unpack "$build/original/fs-2.4.16-py2.py3-none-any.whl" -d "$build/unpacked"
python -m wheel unpack "$build/original/jinja2_fsloader-0.3.0-py2.py3-none-any.whl" -d "$build/unpacked"
git -C "$build/unpacked/fs-2.4.16" apply "$compat/fs.patch"
git -C "$build/unpacked/jinja2_fsloader-0.3.0" apply "$compat/jinja2-fsloader.patch"
python -m wheel pack --build-number 1 "$build/unpacked/fs-2.4.16" -d "$build/wheels"
python -m wheel pack --build-number 1 "$build/unpacked/jinja2_fsloader-0.3.0" -d "$build/wheels"
python -m pip install --force-reinstall --no-index --no-deps --require-hashes \
  --find-links "$build/wheels" -r "$compat/repaired.txt"
python -m pip install --no-deps --only-binary=:all: --require-hashes -r "$compat/runtime.txt"
python -m pip check
