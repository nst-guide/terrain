#! /usr/bin/env bash

# Quit on error
set -e

if [[ $* == *--high_res* ]]
then
    high_res="_hr"
else
    high_res=""
fi

mkdir -p data/unzipped${high_res}/

for dem_file in data/raw${high_res}/*.zip; do
    # get filename without extension
    filename=$(basename -- "${dem_file}")
    extension="${filename##*.}"
    filename="${filename%.*}"

    # Unzip
    # -n: never overwrite
    # apparently has to go _first_
    # https://superuser.com/a/100659
    # -d: extract to directory
    unzip -n $dem_file "*.img" -d data/unzipped${high_res}/
    unzipped_name="data/unzipped${high_res}/${filename}.unzipped"

    echo "Finished unzipping $dem_file"
done
