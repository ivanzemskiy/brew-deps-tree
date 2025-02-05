#!/usr/bin/env zsh

setopt PUSHD_SILENT

pushd $(dirname "$0")/..

    scripts/brew_deps.py -t out

popd
