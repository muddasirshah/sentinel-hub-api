# user this script to generate aoi extent, for which image needs to be downloaded
import os
os.environ['PROJ_LIB'] = 'C:\Users\username\.conda\envs\environmentname\Library\share\proj'
os.environ['GDAL_DATA'] = 'C:\Users\username\.conda\envs\environmentname\Library\share'
import geopandas as gpd #pip install geopandas
from shapely.geometry import box #pip install shapely
# import json

def shapefile_to_geojson_extent(shapefile_path, output_geojson_path):
    gdf = gpd.read_file(shapefile_path)

    bbox = gdf.total_bounds
    bbox_geometry = box(*bbox)
    bbox_gdf = gpd.GeoDataFrame(geometry=[bbox_geometry], crs=gdf.crs)
    bbox_gdf.to_file(output_geojson_path, driver='GeoJSON')

    print(f"Extent GeoJSON saved to: {output_geojson_path}")

if __name__ == "__main__":
    shapefile_path = 'input_vector_file.geojson'
    output_geojson_path = 'extent_file.geojson'
    shapefile_to_geojson_extent(shapefile_path, output_geojson_path)

print("Done")
