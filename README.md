# Hillshade

Generate hillshade and slope angle shading from USGS data.

## Overview

I use [OpenMapTiles](https://github.com/openmaptiles/openmaptiles) to create
self-hosted vector map tiles. However, I'm interested in building a topographic
outdoors-oriented map. A hillshade layer really helps understand the terrain, and just
looks pretty. A slope-angle shading layer is very helpful when recreating in the
outdoors for understanding where is more or less safe to travel.

### Source data

Since my map is focused on the continental United States, I use data from the US
Geological Survey (USGS), which is more accurate but limited to the US. If
you're interested in creating a map with international scope, check out
[30-meter SRTM data](http://dwtkns.com/srtm30m/), which is generally the most
accurate worldwide source available.

Regarding the USGS data, they have a few sources available:

- 1 arc-second seamless DEM. This has ~30m horizontal accuracy, which is
  accurate enough for many purposes, and gives it the smallest file sizes,
  making it easy to work with.
- 1/3 arc-second seamless DEM. This dataset has the best precision available
  (~10m horizontal accuracy) for a seamless dataset. Note that the file sizes
  are about 9x bigger than the 1 arc-second data, making each 1x1 degree cell
  about 450MB unzipped.
- 1/9 arc-second project-based DEM; 1-meter project-based DEM. These have very
  high horizontal accuracy, but aren't available for the entire US yet. If you
  want to use these datasets, go to the [National Map download
  page](https://viewer.nationalmap.gov/basic/), check "Elevation Products
  (3DEP)", and then click "Show Availability" under the layer you're interested
  in, so that you can see if they exist for the area you're interested in.

For my purposes, I use the 1 arc-second data initially for testing, but then the
1/3 arc-second data for production use.

### Terrain RGB

Historically, the way to make a hillshade is to generate raster images where each cell stores the level of grayscale to display.

With Mapbox GL, you have a new option: [Terrain RGB
tiles](https://docs.mapbox.com/help/troubleshooting/access-elevation-data/#mapbox-terrain-rgb).
Instead of encoding the grayscale in the raster, it encodes the _raw elevation
value_ in 0.1m increments. This enables a whole host of cool things to do
client-side, like retrieving elevation for a point, or [generating the
viewshed](https://github.com/nst-guide/viewshed-js) from a point (a work in
progress).

I use Terrain RGB tiles in my projects.

#### Terrarium dataset

If you want to use Terrain RGB tiles, but don't want to create them yourself,
it's also currently possible to use the publicly-hosted Terrarium dataset on
[AWS Public Datasets](https://registry.opendata.aws/terrain-tiles/) for free. It
isn't even in a requester-pays bucket. I don't know how long this will be
available for free, so I figured I'd just generate my own.

If you want to go that route, set this as your source in your `style.json`:

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

Note that I believe the Terrarium dataset uses a different encoding than
Mapbox's RGB tiles.

### Integration with `style.json`

The style JSON spec tells Mapbox GL how to style your map. Add the hillshade
tiles as a source to overlay them with the other sources.

Within `sources`, each object key defines the name by which the later parts of
`style.json` should refer to the layer. Note the difference between a normal
raster layer and the terrain RGB layer.

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
  },
  "terrain-rgb": {
    "type": "raster-dem",
    "tiles": [
      "https://example.com/url/to/tiles/{z}/{x}/{y}.png"
    ],
    "minzoom": 0,
    "maxzoom": 12,
    "encoding": "mapbox"
  }
}
```

Where the `tile.json` for a raster layer should be something like:

```json
{
    "attribution": "<a href=\"https://www.usgs.gov/\" target=\"_blank\">© USGS</a>",
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

Later in the style JSON, refer to the hillshade to style it. Example for terrain
RGB:
```json
{
  "id": "terrain-rgb",
  "source": "terrain-rgb",
  "type": "hillshade",
  "minzoom": 0,
  "paint": {
    "hillshade-shadow-color": "hsl(39, 21%, 33%)",
    "hillshade-illumination-direction": 315,
    "hillshade-exaggeration": 0.8
  },
  "layout": {
    "visibility": "visible"
  }
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
pip install click requests tqdm
```

This also has a dependency on GDAL. I find that the easiest way of installing
GDAL is through Conda:

```
conda create -n hillshade python gdal -c conda-forge
source activate hillshade
pip install click requests tqdm
```

You can also install GDAL via Homebrew on MacOS

```
brew install gdal
```

## Code Overview

#### `download.py`

Downloads USGS elevation data for a given bounding box.

```
> python download.py --help
Usage: download.py [OPTIONS]

Options:
  --bbox TEXT  Bounding box to download data for. Should be west, south, east,
               north.  [required]
  --overwrite  Re-download and overwrite existing files.
  --high_res   Download high-res 1/3 arc-second DEM.
  --help       Show this message and exit.
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

First, download desired DEM tiles, unzip them, build a VRT (Virtual Dataset),
and optionally download my fork of `gdal2tiles` which allows for creating
512x512 pngs.

```bash
# Download for Washington state
python download.py --bbox="-126.7423, 45.54326, -116.9145, 49.00708"
# Or, download high-resolution 1/3 arc-second tiles
python download.py --bbox="-126.7423, 45.54326, -116.9145, 49.00708" --high_res
bash unzip.sh
# Create seamless DEM:
gdalbuildvrt data/dem.vrt data/unzipped/*.img
gdalbuildvrt data/dem_hr.vrt data/unzipped_hr/*.img
# Download my fork of gdal2tiles.py
# I use my own gdal2tiles.py fork for retina 2x 512x512 tiles
git clone https://github.com/nst-guide/gdal2tiles
cp gdal2tiles/gdal2tiles.py ./
```

**Terrain RGB:**

```bash
# Create a new VRT specifically for the terrain RGB tiles, manually setting the
# nodata value to be -9999
gdalbuildvrt -vrtnodata -9999 data/dem_hr_9999.vrt data/unzipped_hr/*.img
gdalwarp -r cubicspline -s_srs EPSG:4269 -t_srs EPSG:3857 -dstnodata 0 -co COMPRESS=DEFLATE data/dem_hr_9999.vrt data/dem_hr_9999_epsg3857.vrt
rio rgbify -b -10000 -i 0.1 --min-z 6 --max-z 13 -j 15 --format webp data/dem_hr_9999_epsg3857.vrt data/terrain_webp.mbtiles
rio rgbify -b -10000 -i 0.1 --min-z 6 --max-z 13 -j 15 --format png data/dem_hr_9999_epsg3857.vrt data/terrain_png.mbtiles
mb-util data/terrain_webp.mbtiles data/terrain_webp
mb-util data/terrain_png.mbtiles data/terrain_png
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

Note, the `data/slope_hr.tif` file in this example, comprised of the bounding
boxes at the bottom, is a 70GB file itself. Make sure you have enough disk
space.

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

Compression:

WebP:

```bash
cd data/color_relief_hr_tiles
for f in */*/*.png; do mkdir -p ../color_relief_hr_tiles_webp/$(dirname $f); cwebp $f -q 80 -o ../color_relief_hr_tiles_webp/$f ; done
```

PNG:

```bash
# Make copy of png files
cp -r data/color_relief_hr_tiles data/color_relief_hr_tiles_png
cd data/color_relief_hr_tiles_png
# Overwrite in place if it can be done without too much quality loss
find . -name '*.png' -print0 | xargs -0 -P8 -L1 pngquant -f --ext .png --quality=70-80 --skip-if-larger
```

### Bboxes used:

For personal reference:

- `-120.8263,32.7254,-116.0826,34.793`
- `-122.4592,35.0792,-117.0546,36.9406`
- `-123.4315,37.0927,-118.0767,37.966`
- `-124.1702,38.0697,-118.5426,38.9483`
- `-124.1702,38.0697,-119.0635,38.9483`
- `-124.5493,39.0475,-120.0647,42.0535`
- `-124.6791,42.0214,-117.0555,46.3334`
- `-124.9103,46.0184,-117.0593,49.0281`
