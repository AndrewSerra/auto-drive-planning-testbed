#!/bin/bash

SCRIPT_PATH=$(dirname $0)

pushd $(realpath $SCRIPT_PATH/..)

cmake -B build/ && \
    cmake --build build/

popd
