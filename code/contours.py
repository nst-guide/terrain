import re
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import boto3
import botocore
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
    '--bucket-prefix',
    default=None,
    type=str,
    help=
    'Root of contours path in S3 bucket. Mbtiles files are saved at {bucket-prefix}/{10m,40ft}/{id}.mbtiles'
)
def main(bbox, high_res, bucket, bucket_prefix):
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
        # A couple urls are ftp. just ignore these for now
        if url.startswith('ftp://'):
            continue
        generate_contours_for_url(
            url=url, bucket=bucket, bucket_prefix=bucket_prefix)


def generate_contours_for_url(url, bucket, bucket_prefix):
    # Check if s3 files already exist
    s3_path_metric = get_s3_path(url, bucket_prefix, metric=True)
    s3_path_imperial = get_s3_path(url, bucket_prefix, metric=False)
    if s3_key_exists(bucket, key=s3_path_metric) and s3_key_exists(
            bucket, key=s3_path_imperial):
        print('s3 path exists; skipping')
        return None

    with TemporaryDirectory() as tmpdir:
        # Download url to local path
        print(url)
        local_path = download_url(url, tmpdir)

        # Unzip DEM
        with open(local_path, 'rb') as f:
            with ZipFile(f) as zf:
                img_file = [x for x in zf.namelist() if x.endswith('.img')][0]
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
                str(mbtiles_path), f'{bucket_prefix}/10m/{mbtiles_path.name}')

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
                str(mbtiles_path), f'{bucket_prefix}/40ft/{mbtiles_path.name}')

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
        # Running as external script was necessary on EC2 to prevent
        # sh [[ not found
        cmd.append('-C')
        cmd.append('\'./metric_prefilter.sh "$@"\'')
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
        # Running as external script was necessary on EC2 to prevent
        # sh [[ not found
        cmd.append('-C')
        cmd.append('\'./imperial_prefilter.sh "$@"\'')
        # Export to data/contour_40ft/*.mbtiles
        mbtiles_path = geojson_path.parents[0] / (
            geojson_path.stem + '.mbtiles')
        cmd.extend(['-o', str(mbtiles_path)])

    # Input geojson
    cmd.append(str(geojson_path))

    s = ' '.join(cmd)
    res = run(s, capture_output=True, shell=True, encoding='utf-8')
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr)
    return mbtiles_path


def get_s3_path(url, bucket_prefix, metric):
    path = bucket_prefix

    if metric:
        path += '/10m/'
    else:
        path += '/40ft/'

    path += (Path(url).stem + '.mbtiles')
    return path


def s3_key_exists(bucket, key):
    """Check if s3 key exists

    From: https://stackoverflow.com/a/33843019
    """
    if not bucket or not key:
        return False

    try:
        s3.Object(bucket, key).load()
    except botocore.exceptions.ClientError as e:
        if e.response['Error']['Code'] == "404":
            # The object does not exist.
            return False
        else:
            # Something else has gone wrong.
            raise botocore.exceptions.ClientError(e)

    return True


if __name__ == '__main__':
    main()
