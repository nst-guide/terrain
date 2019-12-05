# Hillshade

Generate hillshade and slope angle shading from USGS data.

### Terrarium dataset

It's also currently possible to use the publicly-hosted Terrarium dataset
on [AWS Public Datasets](https://registry.opendata.aws/terrain-tiles/) for free.
This is an easy, quick solution if you don't want to generate your own tiles. If
you want to go that route, set this as your source in your `style.json`:

```json
"terrarium": {
  "type": "raster-dem",
  "tiles": [
	"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
  ],
  "minzoom": 0,
  "maxzoom": 15,
  "encoding": "terrarium"
}
```

## Overview

I use [OpenMapTiles](https://github.com/openmaptiles/openmaptiles) to create
self-hosted vector map tiles. However, I'm interested in building a topographic,
outdoors map. A hillshade layer really helps understand the terrain, and just
looks pretty. A slope-angle shading layer is very helpful when recreating in the
outdoors for understanding where is more or less safe to travel.

I'll use the 1 arc-second seamless DEM from the USGS. It would also be possible
to use the 1/3 arc-second seamless data, which is the best seamless resolution
available for the continental US, but those file sizes are 9x bigger, so for now
I’m just going to generate from the 1 arc-second.

In order to integrate this data with OpenMapTiles, after making the hillshade I
need to cut it into raster tiles, and then I can add it as a separate source in
my `style.json`. Something like:

```json
"sources": {
  "openmaptiles": {
    "type": "vector",
    "url": "https://api.maptiler.com/tiles/v3/tiles.json?key={key}"
  },
  "hillshade": {
    "type": "raster",
    "url": "https://example.com/url/to/tile.json",
	"tileSize": 512
  }
}
```

Where the tile.json should be something like:

```json
{
    "attribution": "USGS",
    "description": "Hillshade generated from 1 arc-second USGS DEM",
    "format": "png",
    "id": "hillshade",
    "maxzoom": 16,
    "minzoom": 0,
    "name": "hillshade",
    "scheme": "tms",
    "tiles": ["https://example.com/url/to/tiles/{z}/{x}/{y}.png"],
    "version": "2.2.0"
}
```

## Installation

Clone the repository:

```
git clone https://github.com/nst-guide/hillshade
cd hillshade
```

This is written to work with Python >= 3.6. To install dependencies:

```
pip install click requests
```

This also has a dependency on GDAL. I find that the easiest way of installing
GDAL is through Conda:

```
conda create -n hillshade python gdal -c conda-forge
source activate hillshade
pip install click requests
```

You can also install GDAL via Homebrew on MacOS

```
brew install gdal
```

## Code Overview

#### `download.py`

Downloads USGS elevation data for a given bounding box.

```
python download.py --bbox="west, south, east, north"
```

This script calls the [National Map API](https://viewer.nationalmap.gov/tnmaccess/api/index)
and finds all the 1x1 degree elevation products that intersect the given bounding
box. Right now, this uses 1 arc-second data, which has about a 30 meter
resolution. It would also be possible to use the 1/3 arc-second seamless data,
which is the best seamless resolution available for the continental US, but
those file sizes are 9x bigger, so for now I'm just going to generate from the 1
arc-second.

The script then downloads each of these files to `data/raw/`. By default,
it doesn't re-download and overwrite a file that already exists. If you wish to
overwrite an existing file, use `--overwrite`.

#### `unzip.sh`

Takes downloaded DEM data from `data/raw/`, unzips it, and places it in `data/unzipped/`.

#### `gdaldem`

Use `gdalbuildvrt` to generate a virtual dataset of all DEM tiles, `gdaldem` to
generate a hillshade, and `gdal2tiles` to cut the output raster into map tiles.

`gdaldem` options:

-   `-multidirectional`:

    > multidirectional shading, a combination of hillshading illuminated from 225 deg, 270 deg, 315 deg, and 360 deg azimuth.

-   `s` (scale):

    > Ratio of vertical units to horizontal. If the horizontal unit of the
    > source DEM is degrees (e.g Lat/Long WGS84 projection), you can use
    > scale=111120 if the vertical units are meters (or scale=370400 if they are
    > in feet)

    Note that this won't be exact, since those scale conversions are only really
    valid at the equator, but I had issues warping the VRT to a projection in
    meters, and it's good enough for now.

`gdal2tiles.py` options:

-   `--processes`: number of individual processes to use for generating the base tiles. Change this to a suitable number for your computer.
-   I also use my forked copy of `gdal2tiles.py` in order to generate high-res retina tiles

## Usage

```bash
# Download for Washington state
python download.py --bbox="-126.7423, 45.54326, -116.9145, 49.00708"
bash unzip.sh
# Create seamless DEM:
gdalbuildvrt data/dem.vrt data/unzipped/*.img
gdalbuildvrt data/dem_hr.vrt data/unzipped_hr/*.img
# Download my fork of gdal2tiles.py
# I use my own gdal2tiles.py fork for retina 2x 512x512 tiles
git clone https://github.com/nst-guide/gdal2tiles
cp gdal2tiles/gdal2tiles.py ./
```

**Hillshade:**

```bash
# Generate hillshade
gdaldem hillshade -multidirectional -s 111120 data/dem.vrt data/hillshade.tif
gdaldem hillshade -igor -compute_edges -s 111120 data/dem_hr.vrt data/hillshade_igor_hr.tif

# Cut into tiles
./gdal2tiles.py --processes 10 data/hillshade.tif data/hillshade_tiles
./gdal2tiles.py --processes 10 data/hillshade_igor_hr.tif data/hillshade_igor_hr_tiles
```

**Slope angle shading:**

Note, the `data/slope_hr.tif` file in this example, comprised of the bounding boxes at the bottom, is a 70GB file itself. Make sure you have enough

```bash
# Generate slope
gdaldem slope -s 111120 data/dem.vrt data/slope.tif
gdaldem slope -s 111120 data/dem_hr.vrt data/slope_hr.tif

# Generate color ramp
gdaldem color-relief -alpha -nearest_color_entry data/slope.tif color_relief.txt data/color_relief.tif
gdaldem color-relief -alpha -nearest_color_entry data/slope_hr.tif color_relief.txt data/color_relief_hr.tif

# Cut into tiles
./gdal2tiles.py --processes 10 data/color_relief.tif data/color_relief_tiles
./gdal2tiles.py --processes 10 data/color_relief_hr.tif data/color_relief_hr_tiles
```

### Bboxes used:

-120.8263,32.7254,-116.0826,34.793
-122.4592,35.0792,-117.0546,36.9406
-123.4315,37.0927,-118.0767,37.966
-124.1702,38.0697,-118.5426,38.9483
-124.1702,38.0697,-119.0635,38.9483
-124.5493,39.0475,-120.0647,42.0535
-124.6791,42.0214,-117.0555,46.3334
-124.9103,46.0184,-117.0593,49.0281
