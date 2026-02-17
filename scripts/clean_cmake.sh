#!/bin/bash

SCRIPT_PATH=$(dirname $0)

pushd $(realpath $SCRIPT_PATH/..)

rm -rf build/

if [ -d "CMakeFiles" ]; then
    rm -rf CMakeFiles/
fi

if [ -f "CMakeCache.txt" ]; then
    rm CMakeCache.txt
fi

popd
