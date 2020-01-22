#! /usr/bin/env bash

path=$1
out_dir="data/contour_10m"
temp_dir=$(mktemp -d)
mkdir -p $out_dir

# get filename without extension
filename=$(basename -- "${path}")
extension="${filename##*.}"
filename="${filename%.*}"

# Make VRT
gdalbuildvrt -q $temp_dir/${filename}.vrt $path

# Reproject to EPSG 4326 and also convert data type from float32 to int16
# This solves an out-of-memory error I was encountering with the original
# floating point data
gdalwarp \
    -q \
    -r cubicspline \
    -t_srs EPSG:4326 \
    -ot Int16 \
    -dstnodata -32768 \
    $temp_dir/${filename}.vrt $temp_dir/${filename}_wgs84.vrt

# Generate 10m contours
gdal_contour \
    `# Put elevation values into 'ele_m'` \
    -a ele_m \
    `# Generate contour line every 10 meters` \
    -i 10 \
    `# Export to newline-delimited GeoJSON, so Tippecanoe can read in parallel` \
    -f GeoJSONSeq \
    $temp_dir/${filename}_wgs84.vrt $out_dir/${filename}.geojson
