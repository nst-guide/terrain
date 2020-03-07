# Terrain

Generate contours, hillshade, Terrain RGB, and slope angle shading map tiles
from Digital Elevation Models (DEMs).

## Overview

I use [OpenMapTiles](https://github.com/openmaptiles/openmaptiles) to create
self-hosted vector map tiles. However, I'm interested in building a topographic
outdoors-oriented map. Contours, hillshading, and slope-angle shading are
instrumental in intuitively understanding the terrain.

### Source data

Since my map is focused on the continental United States, I use data from the US
Geological Survey (USGS), which has high accuracy but is limited to the US. If
you're interested in creating a map with international scope, check out
[30-meter SRTM data](http://dwtkns.com/srtm30m/), which is generally the most
accurate worldwide source available. Most of the code in this repository is
applicable to other DEM sources with few modifications.

Regarding the USGS data, they have a few sources available:

- **1 arc-second seamless DEM**. This has ~30m horizontal accuracy, which is
  accurate enough for many purposes, and gives it the smallest file sizes,
  making it easy to work with.
- **1/3 arc-second seamless DEM**. This dataset has the best precision available
  (~10m horizontal accuracy) for a seamless dataset. Note that the file sizes
  are about 9x bigger than the 1 arc-second data, making each 1x1 degree cell
  about 450MB unzipped.
- **1/9 arc-second project-based DEM and 1-meter project-based DEM**. These have very
  high horizontal accuracy, but aren't available for the entire US yet. If you
  want to use these datasets, go to the [National Map download
  page](https://viewer.nationalmap.gov/basic/), check "Elevation Products
  (3DEP)", and then click "Show Availability" under the layer you're interested
  in, so that you can see if they exist for the area you're interested in.

For my purposes, I use the 1 arc-second data initially for testing, but then the
1/3 arc-second data for production use. In a couple years, once more of the
United States is mapped at 1 meter resolution, I'd suggest considering using 1
meter data where available.

### Terrain RGB vs Raster Hillshade

Historically, the way to make a hillshade is to generate raster images where
each cell stores the level of grayscale to display.

With Mapbox GL, you have a new option: [Terrain RGB
tiles](https://docs.mapbox.com/help/troubleshooting/access-elevation-data/#mapbox-terrain-rgb).
Instead of encoding the grayscale in the raster, it encodes the _raw elevation
value_ in 0.1m increments. This enables a whole host of cool things to do
client-side, like retrieving elevation for a point, or generating the viewshed
from a point.

I currently exclusively use Terrain RGB tiles in my projects because it allows for
the possibility of doing cool things in the future if I have time.

#### Terrarium dataset

If you want to use Terrain RGB tiles, but don't want to create them yourself,
it's also currently possible to use the publicly-hosted Terrarium dataset on
[AWS Public Datasets](https://registry.opendata.aws/terrain-tiles/) for free. It
isn't even in a requester-pays bucket. I don't know how long this will be
available for free, so I figured I'd just generate my own.

If you want to go that route, set this as your source in your `style.json` (note
`"encoding": "terrarium"`):

```json
"terrarium": {
  "type": "raster-dem",
  "tiles": [
  	"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
  ],
  "minzoom": 0,
  "maxzoom": 15,
  "tileSize": 256,
  "encoding": "terrarium"
}
```

Note that the Terrarium dataset uses a [different encoding](https://github.com/tilezen/joerd/blob/master/docs/formats.md#terrarium) than Mapbox's RGB
tiles:
```
elevation_m = (red * 256 + green + blue / 256) - 32768
```

### Contours

I originally generated contours vector tiles straight from USGS vector data
([https://github.com/nst-guide/contours](https://github.com/nst-guide/contours)).
These downloads have contour lines pregenerated in vector format, and so are quite
easy to work with; just download, run `ogr2ogr` to convert to GeoJSON, and then
run `tippecanoe` to convert to vector tiles.

There are a couple drawbacks of using the USGS vector contour data:

1. Inconsistent vertical spacing. In some areas, I found that the data included
    10' contours, while others had a precision of only _80'_. Since I desired a
    40' contour, this meant that there were occasionally visual discontinuities
    in the map between tiles with source data of at least 40' precision and
    source data of less than 40' precision.
2. Metric contours. Although I'm currently making maps of the United States,
    where imperial measurements are the standard, it's desirable to provide
    metric measurements as well. With Mapbox GL, it's quite easy to write a
    style expression that converts feet into meters, but the _spacing_ of the
    contour lines will still be in feet. If neighboring imperial contour lines
    are 2000 feet and 2040 feet, displaying those same lines on a metric map
    would represent unintuitive values of 609.6 meters and 621.8 meters.

    In order to display metric contour lines, it is necessary to generate a
    separate set of contours with lines that represent 100 meters, 110 meters,
    etc. This must be generated from the original DEMs.

### Slope-angle shading

Slope angle shading displays polygons representing the slope of the terrain in
degrees. This is just a couple of GDAL functions joined with a color scheme that
roughly matches the one from [Caltopo](http://caltopo.com/).

### Integration with `style.json`

The style JSON spec tells Mapbox GL how to style your map. Add the hillshade
tiles as a source to overlay them with the other sources.

Within `sources`, each object key defines the name by which the later parts of
`style.json` should refer to the layer. Note the difference between a normal
raster layer and the terrain RGB layer.

```json
"sources": {
  "contours": {
    "type": "vector",
    "url": "https://example.com/contours/tile.json"
  },
  "slope_angle": {
    "type": "raster",
    "url": "https://example.com/slope_angle/tile.json",
  	"tileSize": 512
  },
  "terrain-rgb": {
    "type": "raster-dem",
    "url": "https://example.com/terrain_rgb/tile.json",
    "tileSize": 512,
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
  "paint": {
    "hillshade-shadow-color": "hsl(39, 21%, 33%)",
    "hillshade-illumination-direction": 315,
    "hillshade-exaggeration": 0.8
  }
}
```

## Installation

Clone the repository:

```
git clone https://github.com/nst-guide/terrain
cd terrain
```

Then install dependencies
```
conda env create -f environment.yml
source activate terrain
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

Takes downloaded DEM data from `data/raw/` or `data/raw_hr/`, unzips it, and
places it in `data/unzipped/` or `data/unzipped_hr/`.

## Usage

### Preparation

Download desired DEM tiles, then unzip them, build a VRT (Virtual Dataset),
and optionally download my fork of `gdal2tiles` which allows for creating
512x512 pngs.

If you're not using data from the USGS, you'll need to figure out which DEMs to
download yourself. The files should be geospatially adjacent so that there are
no holes in the generated map data.

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

### Terrain RGB

```bash
# Create a new VRT specifically for the terrain RGB tiles, manually setting the
# nodata value to be -9999
gdalbuildvrt \
    `# Set the VRT's nodata value to -9999` \
    -vrtnodata -9999 \
    data/dem_hr_9999.vrt data/unzipped_hr/*.img
# Reproject DEM to web mercator
gdalwarp \
    `# Use cubicspline averaging` \
    -r cubicspline \
    `# Source projection is EPSG 4269` \
    -s_srs EPSG:4269 \
    `# Source projection is EPSG 3857, aka web mercator` \
    -t_srs EPSG:3857 \
    `# Set the destination nodata value to 0` \
    -dstnodata 0 \
    `# Not sure if this does anything outputting to vrt, with TIFF output should compress` \
    -co COMPRESS=DEFLATE \
    data/dem_hr_9999.vrt data/dem_hr_9999_epsg3857.vrt
# Create Mbtiles of terrain rgb data
rio rgbify \
    `# set the base value rgb(0,0,0) to -10000` \
    -b -10000 \
    `# Set the increment to 0.1 meters` \
    -i 0.1 \
    `# Set 6 as minimum zoom level to make tiles` \
    --min-z 6 \
    `# Set 13 as maximum zoom level to make tiles (inclusive)` \
    --max-z 13 \
    `# Use 15 cores` \
    -j 15 \
    `# Create webp images` \
    --format webp \
    data/dem_hr_9999_epsg3857.vrt data/terrain_webp.mbtiles
rio rgbify \
    `# set the base value rgb(0,0,0) to -10000` \
    -b -10000 \
    `# Set the increment to 0.1 meters` \
    -i 0.1 \
    `# Set 6 as minimum zoom level to make tiles` \
    --min-z 6 \
    `# Set 13 as maximum zoom level to make tiles (inclusive)` \
    --max-z 13 \
    `# Use 15 cores` \
    -j 15 \
    `# Create png images` \
    --format png \
    data/dem_hr_9999_epsg3857.vrt data/terrain_png.mbtiles
# Export mbtiles to a directory
# Ideally, I'd use --image_format=webp, but I forgot to do that the first time,
# and don't want to recreate and re-upload all the images, so my WebP images
# have .png extensions (the default)
mb-util data/terrain_webp.mbtiles data/terrain_webp
mb-util data/terrain_png.mbtiles data/terrain_png
```

### Hillshade

Use `gdaldem` to generate a hillshade, and `gdal2tiles` to cut the output raster
into map tiles.

`gdaldem` options:

-   `s` (scale):

    > Ratio of vertical units to horizontal. If the horizontal unit of the
    > source DEM is degrees (e.g Lat/Long WGS84 projection), you can use
    > scale=111120 if the vertical units are meters (or scale=370400 if they are
    > in feet)

    Note that this won't be exact, since those scale conversions are only really
    valid at the equator, but I had issues warping the VRT to a projection in
    meters, and it's good enough for now.

```bash
# Generate hillshade
gdaldem hillshade \
    `# multidirectional shading, a combination of hillshading illuminated from 225 deg, 270 deg, 315 deg, and 360 deg azimuth` \
    -multidirectional \
    `# scale; ratio of vertical units to horizontal. `
    -s 111120 data/dem.vrt data/hillshade.tif
gdaldem hillshade \
    -igor -compute_edges \
    -s 111120 data/dem_hr.vrt data/hillshade_igor_hr.tif

# Cut into tiles
./gdal2tiles.py --processes 10 data/hillshade.tif data/hillshade_tiles
./gdal2tiles.py --processes 10 data/hillshade_igor_hr.tif data/hillshade_igor_hr_tiles
```

### Slope angle shading

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

### Contours

Originally I tried to generate contours by creating a single VRT and then
running `gdal_contour` on it. That fully exhausted the memory and swap on my
computer, however. It's also (usually) unnecessary because Tippecanoe can join features
from neighboring cells. So there's no benefit to having a single huge contour
file over many smaller ones.

Instead, I loop over all downloaded DEM files and run `gdalwarp` and
`gdal_contour` on each one. The definitions for each command are stored in
`make_contours_{10m,40ft}.sh`. Generating contours for each DEM file separately
also has the benefit that it can parallelize. `gdal_contour` appears to be
singlethreaded, while `find` + `xargs` can be run on an arbitrary number of
cores. Memory use is not exceedingly high when contours are created for a single
DEM file.

After the above, I have folders `data/contour_10m/` and `data/contour_40ft` of
contour lines as GeoJSON LineStrings and MultiLineStrings.

Originally I generated contours with all data encoded at zoom 11. These file
sizes were often 500kB each or more, so I decided to limit the amount of data
stored in the tile at zooms 11 and 12, adding all data at zoom 13.

`tippecanoe` is run with `-C`, which defines a shell filter to pass each GeoJSON
feature through. The metric command runs each GeoJSON feature through `jq`; at
zoom 11 or lower contour height must be an even multiple of 50; at zoom 12 they
must be an even multiple of 20; and at zoom 13 all contours are included (10m
intervals are assumed.)

Note however that this choice means that some contour lines will be _removed_
when you zoom from 11 -> 12, because elevations can be a multiple of 50 without
being a multiple of 20. This means that 11.9 -> 12.0 could be a little jagged. I
think ideally I'd have the 12 zoom as a multiple of 25, but since I generated
raw 10m intervals, 25 keeps no more than 50 because 25 isn't in the source
dataset. If you wanted such a seamless zoom, you should generate 25 meter
contours separately, and use `tile-join` and Tippecanoe's zoom options to keep
desired contour spacing at each zoom.

_New method_: generate an imperial and metric mbtiles file for each DEM and put
the mbtiles on S3. Then use `tile-join` on each of the s3 mbtiles to create one
full contours file.

```bash
cd code
python contours.py \
    --bbox '-126.02, 23.72, -65.89, 49.83' \
    --high_res \
    --bucket bucket-name \
    --bucket-prefix contours
```

_Old method_: generate all contour GeoJSON files; then make a single mbtiles at once.

```bash
cpus=14
# Writes GeoJSON contours for each DEM file to data/contour_10m/*.geojson
find data/unzipped_hr/ -type f -name '*.img' -print0 | xargs -0 -P $cpus -L1 bash make_contours_10m.sh
# Writes GeoJSON contours for each DEM file to data/contour_40ft/*.geojson
find data/unzipped_hr/ -type f -name '*.img' -print0 | xargs -0 -P $cpus -L1 bash make_contours_40ft.sh

# Run tippecanoe on 10m contours
tippecanoe \
    `# Set min zoom to 11` \
    -Z11 \
    `# Set max zoom to 13` \
    -z13 \
    `# Read features in parallel; only works with GeoJSONSeq input` \
    -P \
    `# Keep only the ele_m attribute` \
    -y ele_m \
    `# Put contours into layer named 'contour_10m'` \
    -l contour_10m \
    `# Filter contours at different zoom levels` \
    -C 'if [[ $1 -le 11 ]]; then jq "if .properties.ele_m % 50 == 0 then . else {} end"; elif [[ $1 -eq 12 ]]; then jq "if .properties.ele_m % 20 == 0 then . else {} end"; else jq "."; fi' \
    `# Export to contour_10m.mbtiles` \
    -o data/contour_10m.mbtiles \
    data/contour_10m/*.geojson

# Run tippecanoe on 40ft contours
tippecanoe \
    `# Set min zoom to 11` \
    -Z11 \
    `# Set max zoom to 13` \
    -z13 \
    `# Read features in parallel; only works with GeoJSONSeq input` \
    -P \
    `# Keep only the ele_ft attribute` \
    -y ele_ft \
    `# Put contours into layer named 'contour_40ft'` \
    -l contour_40ft \
    `# Filter contours at different zoom levels` \
    -C 'if [[ $1 -le 11 ]]; then jq "if .properties.ele_ft % 200 == 0 then . else {} end"; elif [[ $1 -eq 12 ]]; then jq "if .properties.ele_ft % 80 == 0 then . else {} end"; else jq "."; fi' \
    `# Export to contour_40ft.mbtiles` \
    -o data/contour_40ft.mbtiles \
    data/contour_40ft/*.geojson
```

I tend to export to an `mbtiles` file, because then it's easy to inspect the
generated data with [`mbview`](https://github.com/mapbox/mbview), however I use
[`mb-util`](https://github.com/mapbox/mbutil) to convert the `mbtiles` to a
directory for uploading to S3.
```bash
mb-util data/contour_10m.mbtiles data/contour_10m_tiles --image_format=pbf
mb-util data/contour_40ft.mbtiles data/contour_40ft_tiles --image_format=pbf
```

And then to upload to S3:
```bash
aws s3 cp \
    data/contour_10m_tiles s3://tiles.nst.guide/contour_10m/ \
    --recursive \
    --content-type application/x-protobuf \
    --content-encoding "gzip" \
    `# two week max-age, one year swr` \
    --cache-control "public, max-age=1209600, stale-while-revalidate=31536000"
aws s3 cp \
    data/contour_40ft_tiles s3://tiles.nst.guide/contour_40ft/ \
    --recursive \
    --content-type application/x-protobuf \
    --content-encoding "gzip" \
    `# two week max-age, one year swr` \
    --cache-control "public, max-age=1209600, stale-while-revalidate=31536000"
```


### Compression:

The only output for which I apply compression is the slope angle shading. (If
you're generating plain non-Terrain RGB hillshading I'd compress those too).

Vector tiles generated by Tippecanoe are gzip compressed by default, and Terrain
RGB tiles can't be lossily compressed because that would remove the meaning of
the encoding. PNG and WebP are both already losslessly compressed.

For slope angle shading, I generate lossy WebP tiles and also generate lossy PNG
tiles with pngquant. I actually found that the lossy png files are slightly
smaller than the lossy WebP files in this instance, to my surprise.

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
