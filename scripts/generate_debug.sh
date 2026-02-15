#!/bin/bash

SCRIPT_PATH=$(dirname $0)

pushd $(realpath $SCRIPT_PATH/..)

cmake -B build/ -D CMAKE_BUILD_TYPE=Debug && \
    cmake --build build/

popd
