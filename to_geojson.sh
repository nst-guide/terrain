#! /usr/bin/env bash

# Quit on error
set -e

mkdir -p data/geojson/

for elev_file in data/raw/*GDB.zip; do
    # get filename without extension
    filename=$(basename -- "${elev_file}")
    extension="${filename##*.}"
    filename="${filename%.*}"

    # Get geojson filename
    geojson_name="data/geojson/${filename}.geojson"

    # Only create new geojson files if they don't exist
    if [ ! -f $geojson_name ]; then
        # Create new GeoJSONSeq file using OGR
        ogr2ogr -f GeoJSONSeq $geojson_name $elev_file Elev_Contour
        echo "Finished exporting $elev_file to GeoJSONSeq"
    fi
done
