import re
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import urlretrieve as _urlretrieve

import click
import requests
from tqdm import tqdm


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
@click.option(
    '--high_res',
    is_flag=True,
    default=False,
    help="Download high-res 1/3 arc-second DEM.")
def main(bbox, overwrite, high_res):
    bbox = tuple(map(float, re.split(r'[, ]+', bbox)))
    print(f'Downloading Digital Elevation Models for bbox: {bbox}')
    if high_res:
        download_dir = Path('data/raw_hr')
    else:
        download_dir = Path('data/raw')
    download_dir.mkdir(parents=True, exist_ok=True)
    local_paths = download_dem(
        bbox, directory=download_dir, overwrite=overwrite, high_res=high_res)
    with open('paths.txt', 'w') as f:
        f.writelines(_paths_to_str(local_paths))


def download_dem(bbox, directory, overwrite, high_res):
    """
    Args:
        - bbox (tuple): bounding box (west, south, east, north)
        - directory (pathlib.Path): directory to download files to
        - overwrite (bool): whether to re-download and overwrite existing files
        - high_res (bool): If True, downloads high-res 1/3 arc-second DEM
    """
    urls = get_urls(bbox, high_res)

    local_paths = []
    for url in urls:
        print(f'Downloading url: {url}')
        local_path = download_url(url, directory, overwrite=overwrite)
        if local_path is not None:
            local_paths.append(local_path)

    return local_paths


def get_urls(bbox, high_res, use_best_fit=True):
    """
    Args:
        - bbox (tuple): bounding box (west, south, east, north)
        - high_res (bool): If True, downloads high-res 1/3 arc-second DEM
        - use_best_fit: Filter by bestFitIndex > 0
    """
    url = 'https://viewer.nationalmap.gov/tnmaccess/api/products'
    if high_res:
        product = 'National Elevation Dataset (NED) 1/3 arc-second'
    else:
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
        if use_best_fit:
            return [
                x['downloadURL'] for x in res['items'] if x['bestFitIndex'] > 0]
        else:
            return [x['downloadURL'] for x in res['items']]

    # Otherwise, need to page
    all_results = [*res['items']]
    n_retrieved = len(res['items'])
    n_total = res['total']

    for offset in range(n_retrieved, n_total, n_retrieved):
        params['offset'] = offset
        res = requests.get(url, params=params).json()
        all_results.extend(res['items'])

    # Keep all results with best fit index >0
    if use_best_fit:
        return [x['downloadURL'] for x in all_results if x['bestFitIndex'] > 0]
    else:
        return [x['downloadURL'] for x in all_results]


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


class DownloadProgressBar(tqdm):
    def update_to(self, b=1, bsize=1, tsize=None):
        if tsize is not None:
            self.total = tsize
        self.update(b * bsize - self.n)


def urlretrieve(url, output_path):
    with DownloadProgressBar(unit='B', unit_scale=True, miniters=1,
                             desc=url.split('/')[-1]) as t:
        _urlretrieve(url, filename=output_path, reporthook=t.update_to)


if __name__ == '__main__':
    main()
