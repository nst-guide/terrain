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
    # apparently has to go _first_
    # https://superuser.com/a/100659
    # -d: extract to directory
    unzip -n $dem_file "*.img" -d data/unzipped/
    unzipped_name="data/unzipped/${filename}.unzipped"

    echo "Finished unzipping $dem_file"
done
