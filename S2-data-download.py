import os
# For Coda Environment Uncomment
# os.environ['PROJ_LIB'] = 'C:\Users\username\.conda\envs\environmentname\Library\share\proj'
# os.environ['GDAL_DATA'] = 'C:\Users\username\.conda\envs\environmentname\Library\share'

import sys
parent_dir = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
sys.path.append(parent_dir)
import geopandas as gp
from osgeo import gdal
import traceback
import logging
import json
import numpy as np
import glob
from sentinelhub import SHConfig
from shapely.geometry import Polygon
from fd.utils import BaseConfig, prepare_filesystem
from fd.scripts.download import batch_download
import configparser
import io
import boto3
import warnings
warnings.filterwarnings('ignore')

#Setting the AWS and SH Credentials 
config = configparser.ConfigParser()
config.read('config.ini')
aws_access_key_id = 'your_aws_access_key_id'
aws_secret_access_key =  'your_aws_secret_access_key'
bucket_input_folder = 'aws_bucket_folder_with_geojson_extents'
input_json = 'your_aoi_extent_filename.geojson' #use generate_extent.py to create a geojson file containing the geometry of your AOI and upload that to your aws bucket folder
bucket_output_folder = 'aws_output_folder_where_imagery_will_be_stored' # e.g. imagery/aoiname_Jan01_2019/
output_folder_path = 'local_path_where_image_will_be_downloaded' # e.g. C:\\sentinel-hub-downloads\\aoiname_Jan01_2019  (make sure to create this folder first)
time_from = '2019-01-16' #start_date
time_to = '2019-01-02' #end_date
stacked_file = 'aoiname_Jan01_2019.tif'

output_folder = os.path.abspath(output_folder_path)
grid_name_prefix = input_json.split(".")[0]

print(output_folder)
s3 = boto3.client('s3',
                  aws_access_key_id=aws_access_key_id,
                  aws_secret_access_key=aws_secret_access_key)

sh_config = SHConfig()
# import pdb;pdb.set_trace()
sh_config.sh_client_id = 'your_sentinel_hub_client_id'
sh_config.sh_client_secret = 'your_sentinel_hub_client_secret'
sh_config.aws_secret_access_key = aws_access_key_id
sh_config.aws_access_key_id = aws_secret_access_key


sh_config.save()


base_config = BaseConfig(bucket_name='your_aws_bucket_name',
                         aws_region='your_aws_bucket_region',
                         aws_access_key_id=aws_secret_access_key,
                         aws_secret_access_key=aws_access_key_id)

filesystem = prepare_filesystem(base_config)

# Construct the full file paths using the project_data_root and filenames
PROJECT_DATA_ROOT = bucket_input_folder
INPUT_AOI_FILENAME = input_json
LOCAL_FILEPATH = output_folder

# Read the input AOI file from S3
input_aoi_file = io.BytesIO()
print('eu-central-1',
                    f"{PROJECT_DATA_ROOT}/{INPUT_AOI_FILENAME}",
                    input_aoi_file)
# import pdb; pdb.set_trace()
s3.download_fileobj('your_aws_bucket_name',f"{PROJECT_DATA_ROOT}/{INPUT_AOI_FILENAME}",input_aoi_file)
input_aoi_file.seek(0)
bucket_name = 'your_aws_bucket_name'
aws_region_name = 'your_aws_bucket_region'
sh_client_id = 'your_sentinel_hub_client_id'
sh_client_secret = 'your_sentinel_hub_client_secret'

GRID_FILE_NAME = f"{grid_name_prefix}_grid.gpkg"
grid_file_path = os.path.join(LOCAL_FILEPATH, GRID_FILE_NAME)

# TIME_INTERVAL = config['DEFAULT']['time_interval'].split(',')
TIME_INTERVAL = [time_from, time_to]
BATCH_TIFFS_FOLDER = bucket_output_folder

download_config = {
    "bucket_name": bucket_name,
    "aws_access_key_id": aws_secret_access_key,
    "aws_secret_access_key": aws_access_key_id,
    "aws_region": aws_region_name,
    "sh_client_id": sh_client_id,
    "sh_client_secret": sh_client_secret,
    "description": "Description",
    "aoi_filename": input_aoi_file,
    "grid_filename": grid_file_path,
    "time_interval": TIME_INTERVAL,
    "grid_definition": {
        "grid_id": 1,
        "resolution":10,
        "buffer": [50, 50]
    },

    "tiles_path": BATCH_TIFFS_FOLDER,
    "bands": ["B02", "B03", "B04", "B08", "B11", "dataMask", "CLP"], #bands to download
    "maxcc": 0.99, #max cloud cover 99% cloudy imagery will be downloaded, if this is set to a lower number e.g 0.10 but the cloud cover is 70%, it will not filter the image
    "mosaicking_order": "leastRecent"
}
print("*************************************************************************")
print(download_config)
print("*************************************************************************")

batch_download(download_config)



                      #Mosacking the single time raster tiles into one

s3_client = boto3.client('s3',
                         aws_access_key_id=aws_secret_access_key,
                         aws_secret_access_key=aws_access_key_id)
bucket_name = bucket_name
s3_input_prefix = BATCH_TIFFS_FOLDER

# Defining a function to check if a given S3 object is a band file
def is_band_file(obj):
    return obj['Key'].endswith('.tif') and any(b in obj['Key'] for b in ['B02', 'B03', 'B04', 'B08', 'B11']) #band names

# Recursively list all objects in the bucket and its subfolders
band_objects = []
paginator = s3.get_paginator('list_objects_v2')
for result in paginator.paginate(Bucket=bucket_name, Prefix=s3_input_prefix):
    for obj in result.get('Contents', []):
        if is_band_file(obj):
            band_objects.append(obj)


band_paths = {'B02': [], 'B03': [], 'B04': [], 'B08': [], 'B11': []} # band names
for obj in sorted(band_objects, key=lambda x: x['Key']):
    for band in band_paths:
        if band in obj['Key']:
            band_paths[band].append('/vsis3/{}/{}'.format(bucket_name, obj['Key']))
            break

files_to_mosaic = list(band_paths.values())
for i in files_to_mosaic:
    paths = i[0]
    local_output_path = LOCAL_FILEPATH+'\Mosaic{}'.format(os.path.basename(paths)[-7:])
    g = gdal.Warp(local_output_path, i, format="GTiff", options=["COMPRESS=LZW", "TILED=YES"])
    g = None
    print ("The {} band is Mosaiced".format(local_output_path))




#Stacking the Rasters into stacked band
input_dir = LOCAL_FILEPATH
output_file = os.path.join(LOCAL_FILEPATH, stacked_file)

search_pattern_b02 = os.path.join(input_dir, "MosaicB02.tif")
search_pattern_b03 = os.path.join(input_dir, "MosaicB03.tif")
search_pattern_b04 = os.path.join(input_dir, "MosaicB04.tif")
search_pattern_b08 = os.path.join(input_dir, "MosaicB08.tif")
search_pattern_b11 = os.path.join(input_dir, "MosaicB11.tif")


files = []
files.extend(glob.glob(search_pattern_b02))
files.extend(glob.glob(search_pattern_b03))
files.extend(glob.glob(search_pattern_b04))

files.extend(glob.glob(search_pattern_b08))

files.extend(glob.glob(search_pattern_b11))
array_list = []

desc_list = ['Band2', 'Band3', 'Band4', 'Band8', 'Band11']
print(desc_list)
print(files)

# Read arrays
for file in files:
    src = gdal.Open(file)
    geotransform = src.GetGeoTransform() # Could be done more elegantly outside the for loop
    projection = src.GetProjectionRef()
    array_list.append(src.ReadAsArray())
    src = None

# Stack arrays
stacked_array = np.stack(array_list, axis=0)
array_list = None

# Write to disk
driver = gdal.GetDriverByName('GTiff')
n, rows, cols = stacked_array.shape
dataset = driver.Create(output_file, cols, rows, n,
                                gdal.GDT_UInt16)
dataset.SetGeoTransform(geotransform)
dataset.SetProjection(projection)

for b in range(1,n+1):
    band = dataset.GetRasterBand(b) # GetRasterBand is not zero indexed
    band.WriteArray(stacked_array[b - 1]) # Numpy is zero indexed
    band.SetDescription(desc_list[b - 1])
dataset = None
stacked_array = None
