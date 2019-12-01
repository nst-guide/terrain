import json
import re
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlretrieve

import click
import requests


@click.command()
@click.option('--bbox', required=True, type=str, help='Bounding box, .')
def main(bbox):
    bbox = tuple(map(float, re.split(r'[, ]', bbox)))
    download_dir = Path('data/raw')
    download_dir.mkdir(parents=True, exist_ok=True)
    local_paths = download_contours(bbox, directory=download_dir)
    with open('paths.json', 'w') as f:
        json.dump(_paths_to_str(local_paths), f)


def download_contours(bbox, directory, overwrite=False):
    urls = get_urls(bbox)

    local_paths = []
    for url in urls:
        local_path = download_url(url, directory, overwrite=overwrite)
        local_paths.append(local_path)

    return local_paths


def get_urls(bbox):
    url = 'https://viewer.nationalmap.gov/tnmaccess/api/products'
    product = 'National Elevation Dataset (NED) 1/3 arc-second - Contours'
    extent = '1 x 1 degree'
    fmt = 'FileGDB 10.1'

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
        urlretrieve(url, local_path)

    return local_path.resolve()


def _paths_to_str(paths):
    return [str(path) for path in paths]


if __name__ == '__main__':
    main()
