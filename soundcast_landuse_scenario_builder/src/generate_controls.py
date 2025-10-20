#Copyright [2022] [Puget Sound Regional Council]

#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import geopandas as gpd
import pandas as pd
import numpy as np
import os, pyodbc, sqlalchemy, time
import networkx as nx
import time
from shapely import wkt
from shapely.geometry import Point
import h5py
import yaml
from pathlib import Path
import shutil

def h5_to_data_frame(h5file, integer_cols, table_name):
    """Load h5 tables as Pandas DataFrame object"""
    
    table = h5file[table_name]
    col_dict = {}
    #cols = ['hhno', 'hhtaz']
    for col in table.keys():
        if col == 'sov_ff_time':
            pass
        elif col in integer_cols:
            my_array = np.asarray(table[col]).astype('int')
        else:
            my_array = np.asarray(table[col])
        col_dict[col] = my_array.astype(float)
    return(pd.DataFrame(col_dict))

def update_df(target_df, target_index, update_df, update_index, col_name):
    target_df[col_name] = 0
    target_df.set_index(target_index, inplace = True)
    update_df.set_index(update_index, inplace = True)
    target_df.update(update_df)
    target_df.reset_index(inplace = True)
    update_df.reset_index(inplace = True)

    return target_df


def recode(df, col, new_col, bins, labels, group_by_col):
    category = pd.cut(df[col],bins=bins,labels=labels)
    if new_col in df.columns:
        df = df.drop(columns = [new_col])
    df.insert(len(bins), new_col, category)

    return pd.crosstab(df[group_by_col], df[new_col]).rename_axis(None, axis=1)


config = yaml.safe_load(open("config.yaml"))

# create output dir if it doesn't exist
if not os.path.exists(config['output_dir']):
    os.makedirs(config['output_dir'])

# Setup paths
popsim_run_dir_path = Path(config['output_dir'])
land_use_path = Path(config['input_land_use_path'])
pums_path = Path(config['input_pums_data_path'])
gis_path = Path(config['input_gis_data_path'])

# create sub-directories in popsim folder:
for folder in ['configs','data','output']:
    if os.path.exists(popsim_run_dir_path/folder):
        shutil.rmtree(popsim_run_dir_path/folder)
    os.makedirs(popsim_run_dir_path/folder)


# Load GIS files
# 2 layers are required, including regionwide PUMAs.
# a layer that covers a specific study area that can be altered is provided
# Only households within the study area will be available for allocation
if str(gis_path)[-4:]=='.gdb':
    taz_study_area = gpd.read_file(gis_path, layer=config['taz_layer'])
    # Program will use taz_id & puma_id going forward
    taz_study_area.rename(columns={config['taz_id'] : 'taz_id'}, inplace = True)
    puma_gdf = gpd.read_file(gis_path, layer=config['puma_layer'])
    puma_gdf.rename(columns={config['puma_id'] : 'PUMA'}, inplace = True)
else:
    taz_study_area = gpd.read_file(gis_path/config['taz_layer']/'.shp')
    # Program will use taz_id & puma_id going forward
    taz_study_area.rename(columns={config['taz_id'] : 'taz_id'}, inplace = True)
    puma_gdf = gpd.read_file(gis_path/config['puma_layer']/'.shp')
    puma_gdf.rename(columns={config['puma_id'] : 'PUMA'}, inplace = True)

# Load parcel data from Soundcast input as geoDataframe
parcels_gdf = pd.read_csv(land_use_path/config['parcel_file'], sep = ' ')
parcels_gdf.columns= parcels_gdf.columns.str.lower()
geometry = [Point(xy) for xy in zip(parcels_gdf['xcoord_p'], parcels_gdf['ycoord_p'])]
parcels_gdf = parcels_gdf.drop(['ycoord_p', 'xcoord_p'], axis=1)
parcels_gdf = gpd.GeoDataFrame(parcels_gdf, crs="EPSG:2285", geometry=geometry)

# Load synthetic household and person tables from a Soundcast run
hdf_file = h5py.File(land_use_path/config['synthetic_pop_file'], "r")
persons = h5_to_data_frame(hdf_file, ['id'], 'Person')
hh = h5_to_data_frame(hdf_file, ['id'], 'Household')

# Select parcels that are within the study area
parcels_cols = list(parcels_gdf.columns)
#parcels_cols.extend([config['taz_id'], config['block_group_id'], config['puma_id']])
parcels_cols.extend(['taz_id', 'PUMA'])
parcels_gdf = gpd.sjoin(parcels_gdf, taz_study_area, how='inner')
parcels_gdf = parcels_gdf[[col for col in parcels_cols if col in parcels_gdf.columns]]

# Identify PUMA for a TAZ based on centroid location
taz_points = taz_study_area.copy()
taz_points.geometry = taz_points.geometry.centroid
taz_puma_gdf = gpd.sjoin(taz_points, puma_gdf, how='inner')
taz_puma_gdf = taz_puma_gdf[['taz_id', 'PUMA']]
taz_puma_gdf['region'] = 1

# Write PopulationSim geographic crosswalk between TAZs and PUMAs
#taz_puma_gdf.rename(columns={config['taz_id']:'taz_id', config['puma_id']:'PUMA'}, inplace = True)
for col in taz_puma_gdf.columns:
    taz_puma_gdf[col] = taz_puma_gdf[col].astype('int64')

taz_puma_gdf.to_csv(popsim_run_dir_path/'data'/'geo_cross_walk.csv', index=False)

# Build PopulationSim control file from future land use
# Distribution of household and person characteristics will be applied to any change in totals
study_area_hhs = hh[hh['hhparcel'].isin(parcels_gdf[config['parcel_id']])]
study_area_hhs = update_df(study_area_hhs, 'hhparcel', parcels_gdf, config['parcel_id'], 'taz_id')

study_area_persons = persons[persons['hhno'].isin(study_area_hhs['hhno'])]
study_area_persons = update_df(study_area_persons, 'hhno', study_area_hhs, 'hhno', 'taz_id')

# Get household worker distribution from person table
workers = study_area_persons[study_area_persons['pwtyp']>0]
hh_workers = workers.groupby('hhno').size().reset_index()
hh_workers = hh_workers.rename(columns={0:'hhwkrs'})
study_area_hhs = update_df(study_area_hhs, 'hhno', hh_workers, 'hhno', 'hhwkrs')

# Household categories
col_list = []
# total households:
col_list.append(pd.DataFrame(study_area_hhs.groupby('taz_id').size(), columns = ['hh_taz_weight']))
# households size:
col_list.append(recode(study_area_hhs, 'hhsize', 'num_hh', [0, 1, 2, 3, 4, 5, 6, 200], 
                       ['hh_size_1','hh_size_2', 'hh_size_3', 'hh_size_4', 'hh_size_5', 'hh_size_6', 'hh_size_7_plus'], 'taz_id'))
# workers:
col_list.append(recode(study_area_hhs, 'hhwkrs', 'num_workers', [-1, 0, 1, 2, 999], 
                       ['workers_0','workers_1', 'workers_2', 'workers_3_plus'], 'taz_id'))
# income 
col_list.append(recode(study_area_hhs, 'hhincome', 'income_cat', [-1, 15000, 30000, 60000, 100000, 999999999], 
                       ['income_lt15','income_gt15-lt30', 'income_gt30-lt60', 'income_gt60-lt100', 'income_gt100'], 'taz_id'))

# Person categories
# Total persons
col_list.append(pd.DataFrame(study_area_persons.groupby('taz_id').size(), columns = ['pers_taz_weight']))
# School:
col_list.append(recode(study_area_persons, 'pstyp', 'school', [-1, 0, 100], ['school_no','school_yes'], 'taz_id'))
# Gender:
col_list.append(recode(study_area_persons, 'pgend', 'gender', [0, 1, 100], ['male','female'], 'taz_id'))
# Age:
col_list.append(recode(study_area_persons, 'pagey', 'age', [-1, 19, 35, 60, 999], 
                       ['age_19_and_under', 'age_20_to_35', 'age_35_to_60', 'age_above_60'], 'taz_id'))
# Worker status
col_list.append(recode(study_area_persons, 'pwtyp', 'worker', [0, 999], ['is_worker'], 'taz_id'))

# Race
col_list.append(recode(study_area_persons, 'prace', 'num_hh', [0, 1, 2, 3, 4, 5, 6, 200], 
                       ['white_non_hispanic', 'black_non_hispanic', 'asian_non_hispanic', 'other_non_hispanic', 'two_or_more_races_non_hispanic', 'white_hispanic', 'non_white_hispanic'], 'taz_id'))

df = pd.concat(col_list, axis = 1)
df.reset_index(inplace = True)
#df.rename(columns={config['taz_id']:'taz_id'}, inplace = True)
df['taz_id'] = df['taz_id'].astype('int64')

# For zones in the study area that have no synthetic household data use an average of households in the study area
unpopulated_tazs = taz_study_area[~taz_study_area.taz_id.isin(df.taz_id)][['taz_id']]

df['imputed_regional_dist'] = 0    # Flag to identify this zone had no controled distribution
unpopulated_tazs['imputed_regional_dist'] = 1
df = pd.concat([df, unpopulated_tazs])
df = df.sort_values('taz_id')
df = df.drop_duplicates()

# Check that all TAZs have parcels; if not these should be purposefully excluded from user_allocation.csv
_filter = df['taz_id'].isin(parcels_gdf['taz_p'].unique())
if len(df[~_filter]) > 0:
    for i in df[~df['taz_id'].isin(parcels_gdf['taz_p'].unique())]['taz_id'].values:
        print('no parcels for study area zone: ID: ' + str(i))
    df = df[_filter]

# Define household totals from allocation file
allocate_df = df[['taz_id', 'hh_taz_weight','pers_taz_weight']]
allocate_df.rename(columns={'hh_taz_weight' : 'households', 'pers_taz_weight': 'persons'}, inplace=True)
allocate_df = allocate_df.merge(parcels_gdf.groupby('taz_id')['emptot_p'].sum().reset_index(), how='left', on='taz_id')
allocate_df.rename(columns={'emptot_p' : 'employment'}, inplace=True)
allocate_df.fillna(0, inplace=True)
allocate_df = allocate_df.astype('int')
allocate_df.to_csv(popsim_run_dir_path/'data'/'user_allocation.csv', index=False)
df.fillna(0, inplace=True)

## Enforce integers
df = df.astype('int')
df.to_csv(popsim_run_dir_path/'data'/'future_controls.csv', index=False)

# Create seed hh and person files; include only seed households and persons from PUMAs within the study area
seed_hh = pd.read_csv(pums_path/config['seed_hh_file'])
seed_hh = seed_hh[seed_hh['PUMA'].isin(taz_puma_gdf['PUMA'])]
seed_hh.to_csv(popsim_run_dir_path/'data'/'seed_households.csv', index=False)

seed_persons = pd.read_csv(pums_path/config['seed_person_file'])
seed_persons = seed_persons[seed_persons['hhnum'].isin(seed_hh['hhnum'])]
seed_persons.to_csv(popsim_run_dir_path/'data'/'seed_persons.csv', index=False)