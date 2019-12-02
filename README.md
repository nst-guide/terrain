# contours

Generate vector tile contour data from USGS data

## Overview

#### `download.py`

Downloads USGS contour data for a given bounding box.

```
python download.py --bbox="west, south, east, north"
```

This script calls the [National Map API](https://viewer.nationalmap.gov/tnmaccess/api/index)
and finds all the 1x1 degree contour products that intersect the given bounding
box. The script then downloads each of these files to `data/raw/`. By default,
it doesn't re-download and overwrite a file that already exists. If you wish to
overwrite an existing file, use `--overwrite`.

#### `to_geojson.sh`

Takes downloaded GeoDatabase contour data from `data/raw/` and uses `ogr2ogr` to
turn them into GeoJSON line-delimited data, placed in `data/geojson/`. By
default, it runs `ogr2ogr` on every downloaded GeoDatabase file, and currently
it's not possible to select only specific files to convert.

GeoJSON line-delimited is helpful because that allows Tippecanoe to run in parallel.

#### `tippecanoe`

This turns the contour data into Mapbox Vector Tiles, ready to be served.

Options:

- `-Z11`: Set the minimum zoom to 11. Tippecanoe won't create any overview tiles.
- `-zg`: Let Tippecanoe guess the maximum zoom level. It seems from testing that it selects `11`, i.e. that 11 is high enough to represent the contours
- `-P`: run in parallel. If the GeoJSON files are not line-delimited, won't actually run in parallel.
- `--extend-zooms-if-still-dropping`: Not sure if this actually does anything since I'm not using `--drop-densest-as-needed`.
- `-y`: only keep the provided attributes in the MVT. I think the only metadata needed for styling is `FCode`, which determines whether it's a multiple of 200' and should be styled darker, and `ContourElevation`, which stores the elevation itself. I haven't checked if you can do modular arithmetic on the fly in the Mapbox style specification, but if you can then you could leave out `FCode`.
- `-l`: combine all files into a single layer named `Elev_Contour`. Otherwise, it would create a different layer in the vector tiles for each provided file name
- `-o`: output file name. If you want a directory of vector tiles instead of a `.mbtiles` file, use `-e`
- `data/geojson/*.geojson`: path to input data

## Usage

```bash
# Download for Washington state
python download.py --bbox="-126.7423, 45.54326, -116.9145, 49.00708"
bash to_geojson.sh
tippecanoe \
    -Z11 \
    -zg \
    -P \
    --extend-zooms-if-still-dropping \
    -y FCode -y ContourElevation \
    -l Elev_Contour \
    -o contours.mbtiles \
    data/geojson/*.geojson
```