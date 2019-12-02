#! /usr/bin/env bash

# Quit on error
set -e

mkdir -p data/unzipped/

for dem_file in data/raw/*.zip; do
    # get filename without extension
    filename=$(basename -- "${dem_file}")
    extension="${filename##*.}"
    filename="${filename%.*}"

    # Unzip
    # -n: never overwrite
    # -d: extract to directory
    unzip $dem_file "*.img" -d data/unzipped/ -n
    unzipped_name="data/unzipped/${filename}.unzipped"

    echo "Finished unzipping $dem_file"
done
