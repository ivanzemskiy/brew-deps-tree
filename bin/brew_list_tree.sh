#!/usr/bin/env zsh

setopt PUSHD_SILENT

pushd $(dirname "$0")/..

    brew deps --tree --installed > brew_list_tree.txt

popd