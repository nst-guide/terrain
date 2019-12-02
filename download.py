import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlretrieve

import click
import requests


@click.command()
@click.option(
    '--bbox',
    required=True,
    type=str,
    help='Bounding box to download data for. Should be west, south, east, north.'
)
@click.option(
    '--overwrite',
    is_flag=True,
    default=False,
    help="Re-download and overwrite existing files.")
def main(bbox, overwrite):
    bbox = tuple(map(float, re.split(r'[, ]+', bbox)))
    print(f'Downloading contour datasets for bbox: {bbox}')
    download_dir = Path('data/raw')
    download_dir.mkdir(parents=True, exist_ok=True)
    local_paths = download_dem(
        bbox, directory=download_dir, overwrite=overwrite)
    with open('paths.txt', 'w') as f:
        f.writelines(_paths_to_str(local_paths))


def download_dem(bbox, directory, overwrite=False):
    urls = get_urls(bbox)

    local_paths = []
    for url in urls:
        print(f'Downloading url: {url}')
        local_path = download_url(url, directory, overwrite=overwrite)
        if local_path is not None:
            local_paths.append(local_path)

    return local_paths


def get_urls(bbox):
    url = 'https://viewer.nationalmap.gov/tnmaccess/api/products'
    product = 'National Elevation Dataset (NED) 1 arc-second'
    extent = '1 x 1 degree'
    fmt = 'IMG'

    params = {
        'datasets': product,
        'bbox': ','.join(map(str, bbox)),
        'outputFormat': 'JSON',
        'version': 1,
        'prodExtents': extent,
        'prodFormats': fmt}

    res = requests.get(url, params=params)
    res = res.json()

    # If I don't need to page for more results, return
    if len(res['items']) == res['total']:
        return [x['downloadURL'] for x in res['items'] if x['bestFitIndex'] > 0]

    # Otherwise, need to page
    all_results = [*res['items']]
    n_retrieved = len(res['items'])
    n_total = res['total']

    for offset in range(n_retrieved, n_total, n_retrieved):
        params['offset'] = offset
        res = requests.get(url, params=params).json()
        all_results.extend(res['items'])

    # Keep all results with best fit index >0
    return [x['downloadURL'] for x in all_results if x['bestFitIndex'] > 0]


def download_url(url, directory, overwrite=False):
    # Cache original download in self.raw_dir
    parsed_url = urlparse(url)
    filename = Path(parsed_url.path).name
    local_path = Path(directory) / filename
    if overwrite or (not local_path.exists()):
        try:
            urlretrieve(url, local_path)
        except HTTPError:
            print(f'File could not be downloaded:\n{url}')
            return None

    return local_path.resolve()


def _paths_to_str(paths):
    return [str(path) for path in paths]


if __name__ == '__main__':
    main()
