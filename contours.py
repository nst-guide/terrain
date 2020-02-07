import re
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import click

from download import download_url, get_urls


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
@click.option(
    '-o',
    '--output-dir',
    required=True,
    type=click.Path(file_okay=False, dir_okay=True, writable=True))
def main(bbox, high_res, output_dir):
    """Generate contours sequentially
    """
    if bbox is None:
        # Bounding box of continental US
        bbox = (-126.02, 23.72, -65.89, 49.83)
    else:
        bbox = tuple(map(float, re.split(r'[, ]+', bbox)))

    # Get list of files
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    urls = get_urls(bbox, high_res=high_res, use_best_fit=False)
    for url in urls:
        with TemporaryDirectory() as tmpdir:
            # Download url to local path
            local_path = download_url(url, tmpdir)

            # Unzip DEM
            with open(local_path, 'rb') as f:
                with ZipFile(f) as zf:
                    img_file = [
                        x for x in zf.namelist() if x.endswith('.img')][0]
                    unzipped_path = zf.extract(img_file, path=tmpdir)

            # Generate metric contours
            # outputs hardcoded to data/contours_10m
            cmd = ['bash', 'make_contours_10m.sh', unzipped_path]
            run(cmd, check=True)

            # Generate imperial contours
            # outputs hardcoded to data/contours_40ft
            cmd = ['bash', 'make_contours_40ft.sh', unzipped_path]
            run(cmd, check=True)

if __name__ == '__main__':
    main()
