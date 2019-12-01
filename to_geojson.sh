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

    # Delete existing file
    rm -f $geojson_name

    # Create new GeoJSONSeq file using OGR
    ogr2ogr -f GeoJSONSeq $geojson_name $elev_file Elev_Contour
    echo "Finished exporting $elev_file to GeoJSONSeq"
done
