#!/bin/bash

SCRIPT_PATH=$(dirname $0)

pushd $(realpath $SCRIPT_PATH/..)

rm -rf build/

popd
