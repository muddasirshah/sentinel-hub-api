
**Sentinel-1 and Sentinel-2 Data Processing Pipeline**


S1_data_downlaod and S2_data_downlaod are the Python scripts for processing Sentinel-1 radar and Sentinel-2 data. The scripts downloads data from Sentinel Hub, mosaics single time raster tiles, stacks them into stacked band, and saves the resulting file to a local directory.
They uses the following libraries: os, sys, geopandas, osgeo.gdal, traceback, logging, json, numpy, glob, rasterio, sentinelhub, shapely.geometry, configparser, io, boto3, and warnings.

Before running the script, you need to create a config.ini file in the same directory as the script. The config.ini file should contain the following credentials:

1. aws_access_key_id
2. aws_secret_access_key
3. sh_client_id
4. sh_client_secret
5. bucket_name
6. aws_region
7. project_data_root
8. input_aoi_filename
9. local_filepath
10. grid_file_name
11. time_interval
12. batch_tiffs_folder
13. An AOI file (input_aoi_filename) that defines the area of interest.
14. A grid file (grid_file_name) that defines the grid for the downloaded data.

The scripts read the config.ini file and sets up the AWS and Sentinel Hub credentials using boto3 and sentinelhub libraries respectively. Then it constructs the full file paths using the project_data_root and filenames, reads the input AOI file from S3, and defines the download parameters, including the grid definition and bands to be downloaded. The downloaded images are saved in the specified batch_tiffs_folder.

The script then mosaics the single time raster tiles into one using gdal. The final mosaiced image is saved in a local_output_path.

**Getting Started**
**Prerequisites**

To run these script, you'll need to have the following installed on your computer:

1. Python 3.6 or later
2. geopandas
3. osgeo
4. traceback
5. logging
6. json
7. numpy
8. glob
9. rasterio
10. sentinelhub
11. shapely
12. configparser
13. io
14. boto3

**Installation**

You can install all of the necessary dependencies by running the following command:

`pip install -r requirements.txt`
<br>
For conda environment first create an environment with python=3.9.5 and then run the `setup.py` file

<b> conda create -n environmentname python=3.9.5 gdal</b> <br>
<b> conda activate environmentname </b><br>
<b> pip install pyproj </b><br>
Change username and environmentname after importing os module if you are using the GDAL scripts with conda environment <br>
<b> import os</b> <br>
<b> os.environ['PROJ_LIB'] = 'C:\\Users\\username\\.conda\\envs\\environmentname\\Library\\share\\proj' </b><br>
<b> os.environ['GDAL_DATA'] = 'C:\\Users\\username\\.conda\\envs\\environmentname\\Library\\share' </b>

<br> 
use the generate_extent.py to create a geojson extent (bounds) of your vector layer

**Usage**


To use this scripts, you'll need to provide the following:


`python S1_data_downlaod.py`
`python S2_data_downlaod.py`


**Contributing**

If you find a bug or have a feature request, please open an issue on GitHub. If you'd like to contribute to the project, please fork the repository and submit a pull request.





