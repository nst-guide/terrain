import re
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import boto3
import click

from download import download_url, get_urls

s3 = boto3.resource('s3')


@click.command()
@click.option(
    '--bbox',
    required=False,
    default=None,
    type=str,
    help='Bounding box to download data for. Should be west, south, east, north.'
)
@click.option(
    '--high_res',
    is_flag=True,
    default=False,
    help="Download high-res 1/3 arc-second DEM.")
@click.option('--bucket', default=None, type=str, help='S3 bucket')
@click.option(
    '--bucket-path',
    default=None,
    type=str,
    help='Root of contours path in S3 bucket')
def main(bbox, high_res, bucket, bucket_path):
    """Generate contours sequentially
    """
    if bbox is None:
        # Bounding box of continental US
        bbox = (-126.02, 23.72, -65.89, 49.83)
    else:
        bbox = tuple(map(float, re.split(r'[, ]+', bbox)))

    # Get list of files
    urls = get_urls(bbox, high_res=high_res, use_best_fit=False)
    for url in urls:
        with TemporaryDirectory() as tmpdir:
            # Download url to local path
            print(url)
            local_path = download_url(url, tmpdir)

            # Unzip DEM
            with open(local_path, 'rb') as f:
                with ZipFile(f) as zf:
                    img_file = [
                        x for x in zf.namelist() if x.endswith('.img')][0]
                    unzipped_path = zf.extract(img_file, path=tmpdir)

            # Generate metric contours
            # outputs hardcoded to data/contours_10m
            print('generating metric contours')
            cmd = ['bash', 'make_contours_10m.sh', unzipped_path]
            run(cmd, check=True)

            if bucket is not None:
                gj_path = Path('data/contour_10m') / (
                    Path(unzipped_path).stem + '.geojson')
                assert gj_path.exists(), 'file does not exist'
                print('generating metric mbtiles')
                mbtiles_path = run_tippecanoe(gj_path, metric=True)

                # Write mbtiles to S3
                s3.Bucket(bucket).upload_file(
                    str(mbtiles_path), f'{bucket_path}/10m/{mbtiles_path.name}')

                # Delete geojson and mbtiles
                Path(gj_path).unlink(missing_ok=True)
                Path(mbtiles_path).unlink(missing_ok=True)

            # Generate imperial contours
            # outputs hardcoded to data/contours_40ft
            print('generating imperial contours')
            cmd = ['bash', 'make_contours_40ft.sh', unzipped_path]
            run(cmd, check=True)

            if bucket is not None:
                gj_path = Path('data/contour_40ft') / (
                    Path(unzipped_path).stem + '.geojson')
                assert gj_path.exists(), 'file does not exist'
                print('generating imperial mbtiles')
                mbtiles_path = run_tippecanoe(gj_path, metric=False)

                # Write mbtiles to S3
                s3.Bucket(bucket).upload_file(
                    str(mbtiles_path),
                    f'{bucket_path}/40ft/{mbtiles_path.name}')

                # Delete geojson and mbtiles
                Path(gj_path).unlink(missing_ok=True)
                Path(mbtiles_path).unlink(missing_ok=True)


def run_tippecanoe(geojson_path, metric=False):
    cmd = [
        'tippecanoe',
        # Set min zoom to 11
        '-Z11',
        # Set max zoom to 13
        '-z13',
        # Read features in parallel; only works with GeoJSONSeq input
        '-P',
        # overwrite
        '--force']

    if metric:
        # Keep only the ele_m attribute
        cmd.extend(['-y', 'ele_m'])
        # Put contours into layer named 'contour_10m'
        cmd.extend(['-l', 'contour_10m'])
        # Filter contours at different zoom levels
        cmd.append('-C')
        cmd.append('./metric_prefilter.sh')
        # Export to data/contour_10m/*.mbtiles
        mbtiles_path = geojson_path.parents[0] / (
            geojson_path.stem + '.mbtiles')
        cmd.extend(['-o', str(mbtiles_path)])
    else:
        # Keep only the ele_ft attribute
        cmd.extend(['-y', 'ele_ft']) \
        # Put contours into layer named 'contour_40ft'

        cmd.extend(['-l', 'contour_40ft'])
        # Filter contours at different zoom levels
        cmd.append('-C')
        cmd.append('./imperial_prefilter.sh')
        # Export to data/contour_40ft/*.mbtiles
        mbtiles_path = geojson_path.parents[0] / (
            geojson_path.stem + '.mbtiles')
        cmd.extend(['-o', str(mbtiles_path)])

    # Input geojson
    cmd.append(str(geojson_path))

    s = ' '.join(cmd)
    run(s, check=True, stdout=True, stderr=True, shell=True)
    return mbtiles_path


if __name__ == '__main__':
    main()
