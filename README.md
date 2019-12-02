# contours

Generate vector tile contours from USGS data.

## Overview

I use [OpenMapTiles](https://github.com/openmaptiles/openmaptiles) to self-host
vector map tiles. However, I'm interested in building a topographic, outdoors
map, and so I need contour lines. The USGS releases [1x1 degree 40' contour line data][contours]
generated from their 1/3 arc-second seamless DEM. In order to integrate this data with OpenMapTiles, I need to cut the contour lines into vector tiles, and then I can add them as a separate source in my `style.json`. Something like:

```json
"sources": {
  "openmaptiles": {
    "type": "vector",
    "url": "https://api.maptiler.com/tiles/v3/tiles.json?key={key}"
  },
  "contours": {
    "type": "vector",
    "url": "https://example.com/url/to/tile.json"
  }
}
```

Where the tile.json should be something like:
```json
{
	"attribution": "USGS",
	"description": "USGS 40' contour lines",
	"format": "pbf",
	"id": "contours",
	"maxzoom": 16,
	"minzoom": 11,
	"name": "contours",
	"scheme": "xyz",
	"tiles": ["https://example.com/url/to/tiles/{z}/{x}/{y}.pbf"],
	"version": "2.0.0"
}
```

[contours]: https://www.sciencebase.gov/catalog/items?q=&filter=tags%3DNational+Elevation+Dataset+%28NED%29+1%2F3+arc-second+-+Contours

## Installation

Clone the repository:
```
git clone https://github.com/nst-guide/contours
cd contours
```

This is written to work with Python >= 3.6. To install dependencies:
```
pip install click requests
```

This also has dependencies on GDAL and
[`tippecanoe`](https://github.com/mapbox/tippecanoe). I find that the easiest
way of installing GDAL and tippecanoe is through Conda:
```
conda create -n contours python gdal tippecanoe -c conda-forge
source activate contours
pip install click requests
```

You can also install GDAL and Tippecanoe via Homebrew on MacOS
```
brew install gdal tippecanoe
```

## Code Overview

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