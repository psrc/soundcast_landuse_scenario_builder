from pydantic import BaseModel, validator
from typing import List, Optional
import typing
from pathlib import Path

class ValidateSettings(BaseModel):
    # Set data and user input location
    configs_dir: str
    input_land_use_path: str
    input_pums_data_path: str
    input_gis_data_path: str
    # PUMS data year
    pums_year: int
    # File names. Most likely, these will remain unchanged. 
    parcel_file: str
    synthetic_pop_file: str
    puma_layer: str
    taz_layer: str

    # Output dir. This is where the inputs to populationsim will reside. 
    # Warning- this entire directory will be over-written. 
    output_dir: str

    # Results for only study area TAZs can be updated if True
    # If False, only synthetic records will be written to h5 file
    # Set to True for limited sub-area analysis or False for full-scale regional analysis
    update_existing_h5: bool

    update_jobs: bool
    update_hh: bool
    update_persons: bool

    taz_id: str
    block_group_id: str
    puma_id: str
    parcel_id: str

    household_cols: list[str] 

    person_cols: list[str] 