#! /usr/bin/env bash

path=$1
out_dir="data/contour_40ft"
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

# Convert DEM to feet
# gdal_translate is preferable over gdal_calc.py, because the latter can't write
# to a VRT
# https://geozoneblog.wordpress.com/2016/06/20/converting-vertical-units-dem/d
gdal_translate \
    -q \
    -scale 0 0.3048 0 1 \
    $temp_dir/${filename}_wgs84.vrt $temp_dir/${filename}_wgs84_feet.vrt

# Generate 40ft contours
gdal_contour \
    `# Put elevation values into 'ele_ft'` \
    -a ele_ft \
    `# Generate contour line every 40 feet` \
    -i 40 \
    `# Export to newline-delimited GeoJSON, so Tippecanoe can read in parallel` \
    -f GeoJSONSeq \
    $temp_dir/${filename}_wgs84_feet.vrt $out_dir/${filename}.geojson
