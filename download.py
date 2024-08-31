#
# Copyright (c) Sinergise, 2019 -- 2021.
#
# This file belongs to subproject "field-delineation" of project NIVA (www.niva4cap.eu).
# All rights reserved.
#
# This source code is licensed under the MIT license found in the LICENSE
# file in the root directory of this source tree.
#

import json
import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from typing import List

import geopandas as gpd
from dateutil.parser import parse
from fs_s3fs import S3FS
from shapely.geometry import Polygon
from tqdm.auto import tqdm

from sentinelhub import Geometry, CRS, BatchSplitter, SentinelHubBatch, SentinelHubRequest, DataCollection, \
    BatchRequest, BatchRequestStatus
from .utils import BaseConfig, set_sh_config

LOGGER = logging.getLogger(__name__)


@dataclass
class DownloadConfig(BaseConfig):
    sh_client_id: str
    sh_client_secret: str
    aoi_filename: str
    time_interval: tuple
    data_collection: DataCollection
    grid_definition: dict
    tiles_path: str
    maxcc: float = 1.0
    mosaicking_order: str = 'leastRecent'


def get_number_of_vertices(aoi: Geometry) -> int:
    """ Return number of points on geometry exterior. Technically, we should also count holes...
    """
    geometry = [aoi.geometry] if isinstance(aoi.geometry, Polygon) else aoi.geometry
    return sum(len(poly.exterior.coords) for poly in geometry)


def simplify_geometry(aoi: Geometry,
                      tolerance: float = 0.004,
                      max_count: int = 1500) -> Geometry:
    """
    Simplify input geometry such that number of vertices can be processed by batch process API
    """
    vertex_count = get_number_of_vertices(aoi)

    LOGGER.info(f'Number of vertices of original geometry: {vertex_count}')

    if vertex_count > max_count:
        geometry = aoi.geometry.simplify(tolerance, preserve_topology=True)
        aoi = Geometry(geometry, crs=aoi.crs)

    LOGGER.info(f'Number of vertices after simplification: {get_number_of_vertices(aoi)}')

    return aoi


def plot_batch_splitter(splitter: BatchSplitter):
    """ Plots tiles and area geometry from a splitter class
    """
    gdf = get_batch_tiles(splitter)
    ax = gdf.plot(column='status', legend=True, figsize=(10, 10))

    area_series = gpd.GeoSeries(
        [splitter.get_area_shape()],
        crs=splitter.crs.pyproj_crs()
    )
    area_series.plot(ax=ax, facecolor='none', edgecolor='black')


def get_batch_tiles(splitter: BatchSplitter) -> gpd.GeoDataFrame:
    tile_geometries = [Geometry(bbox.geometry, bbox.crs) for bbox in splitter.get_bbox_list()]
    tile_geometries = [geometry.transform(splitter.crs) for geometry in tile_geometries]

    return gpd.GeoDataFrame(
        {
            'id': [info['id'] for info in splitter.get_info_list()],
            'name': [info['name'] for info in splitter.get_info_list()],
            'status': [info['status'] for info in splitter.get_info_list()]
        },
        geometry=[geometry.geometry for geometry in tile_geometries],
        crs=splitter.crs.pyproj_crs()
    )


def get_tile_status_counts(batch: SentinelHubBatch, request: BatchRequest) -> dict:
    """ Returns counts how many tiles have a certain status
    """
    stats = {}

    for tile in batch.iter_tiles(batch_request=request):
        status = tile['status']
        stats[status] = stats.get(status, 0) + 1

    return stats


def monitor_batch_job(batch: SentinelHubBatch, batch_request: BatchRequest, sleep_time: int = 120):
    """ Keeps checking number of processed tiles until the batch request finishes. During the process it shows a
    progress bar and at the end it logs if any tiles failed
    """
    batch_request = batch.get_request(batch_request)
    while batch_request.status in [BatchRequestStatus.CREATED, BatchRequestStatus.ANALYSING]:
        time.sleep(5)
        batch_request = batch.get_request(batch_request)

    with tqdm(total=batch_request.tile_count) as progress_bar:
        finished_count = 0
        while True:
            tile_counts = get_tile_status_counts(batch, batch_request)
            new_finished_count = tile_counts.get('PROCESSED', 0) + tile_counts.get('FAILED', 0)

            progress_bar.update(new_finished_count - finished_count)
            finished_count = new_finished_count

            all_count = sum(tile_counts.values())
            if finished_count == all_count:
                success_count = tile_counts.get('PROCESSED', 0)
                if success_count < all_count:
                    LOGGER.info('Some tiles failed: %s', str(tile_counts))
                    raise RuntimeError(f'Batch job failed for {all_count - success_count} tiles')
                break

            time.sleep(sleep_time)


def load_dates(filesystem: S3FS, tile_name: str) -> List[datetime]:
    """ Load a json file with dates from the bucket and parse out dates
    """
    path = f'/{tile_name}/userdata.json'

    with filesystem.open(path, 'r') as fp:
        userdata = json.load(fp)

    dates_list = json.loads(userdata['dates'])

    return [parse(date) for date in dates_list]


def load_evalscript():
    """ Load hte evalscript for the batch request, either requesting timestamps or imaging data
    """
    evalscript_dir = os.path.join(os.path.dirname(__file__), 'evalscripts')

    with open(f'{evalscript_dir}/data_evalscript.js', 'r') as fp:
        evalscript = fp.read()

    LOGGER.info(evalscript)

    return evalscript


def create_batch_request(batch: SentinelHubBatch,
                         config: DownloadConfig,
                         output_responses: List[dict],
                         description: str = 'Batch request') -> BatchRequest:
    """ Helper function that creates a SH batch request
    """
    LOGGER.info('Read and simplify AOI geometry')
    aoi_gdf = gpd.read_file(config.aoi_filename)
    assert aoi_gdf.crs.name == 'WGS 84'
    aoi = Geometry(aoi_gdf.geometry.values[0], crs=CRS.WGS84)
    aoi = simplify_geometry(aoi)

    LOGGER.info('Set up SH and AWS credentials')
    _ = set_sh_config(config)

    LOGGER.info('This evalscript is executed')
    evalscript = load_evalscript()

    sentinelhub_request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=config.data_collection,
                time_interval=config.time_interval,
                maxcc=config.maxcc,
                mosaicking_order=config.mosaicking_order
            )
        ],
        responses=output_responses,
        geometry=aoi
    )

    batch_request = batch.create(
        sentinelhub_request=sentinelhub_request,
        tiling_grid=SentinelHubBatch.tiling_grid(
            **config.grid_definition
        ),
        output=SentinelHubBatch.output(
            default_tile_path=f's3://{config.bucket_name}/{config.tiles_path}/<tileName>/<outputId>.<format>',
            skip_existing=False,
            overwrite=True
        ),
        description=description
    )

    return batch_request
