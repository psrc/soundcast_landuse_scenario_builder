import os
from urllib.request import urlopen
from zipfile import ZipFile
import io
import pandas as pd
import us


def download_pums_data(pums_year, pums_table, pums_data_dir, state_id=53, overwrite=True):
    """
    Download PUMS data for specified year, table (household or person), and state.
    Parameters:
    - pums_year: int, e.g. 2021
    - pums_table: str, "h" for household or "p" for person
    - pums_data_dir: str, directory to save PUMS data
    - state_id: int, FIPS code for state, default is 53 (Washington)
    - overwrite: bool, whether to overwrite existing files, default is True
    Returns:
    - pandas DataFrame of the requested PUMS data"""

    # create the pums_data_dir if it doesn't exist
    os.makedirs(pums_data_dir, exist_ok=True)
    # state_id can be passed as an argument, but default is WA (53)
    state_id_str = str(state_id).zfill(2)
    state_abbr = us.states.mapping('fips', 'abbr')[state_id_str].lower()
    # file name format is psam_{pums_table}{state_id_str}.csv, e.g. psam_h53.csv for WA household data
    file_name = f"psam_{pums_table}{state_id_str}.csv"
    file_path = os.path.join(pums_data_dir, file_name)
    if os.path.exists(file_path):
        if overwrite:
            os.remove(file_path)
            print(f"Deleted existing file: {file_path}")
        else:
            print(f"File already exists, skipping download: {file_path}")
            return pd.read_csv(file_path)

    pums_url = f"https://www2.census.gov/programs-surveys/acs/data/pums/{pums_year}/5-Year/csv_{pums_table}{state_abbr}.zip"
    r = urlopen(pums_url).read()
    archive = ZipFile(io.BytesIO(r))
    archive.extract(file_name, pums_data_dir)
    print(f"Downloaded and extracted: {file_name} to {pums_data_dir}")
    return pd.read_csv(file_path)

def prepare_pums_data(pums_hh,pums_person,pums_year):
    # Remove group quarters records
    if pums_year > 2020:
        pums_hh = pums_hh[pums_hh['TYPEHUGQ'].isin([1])]
    else:
        pums_hh = pums_hh[pums_hh['TYPE'].isin([1,2])]

    # Filter for person/household matches
    pums_person = pums_person[pums_person['SERIALNO'].isin(pums_hh['SERIALNO'])].copy()
    pums_hh = pums_hh[pums_hh['SERIALNO'].isin(pums_person['SERIALNO'])].copy()
    pums_person.index = pums_person['SERIALNO']
    pums_hh.index = pums_hh['SERIALNO']

    # Generate unique household ID "hhnum"
    pums_hh['hhnum'] = [i+1 for i in range(len(pums_hh))]
    pums_person['hhnum'] = 0
    pums_person.update({'hhnum':pums_hh.hhnum})

    # Calculate household workers based on person records
    pums_person['is_worker'] = 0
    pums_person.loc[pums_person['ESR'].isin([1,2,4,5]), 'is_worker'] = 1
    worker_count = pums_person.groupby('hhnum').sum()[['is_worker']]
    pums_hh['worker_count'] = -99
    pums_hh.index = pums_hh.hhnum
    pums_hh.update({'worker_count': worker_count.is_worker})
    
    # adjust income of pre pums_year records to match pums_year dollars
    pums_hh['HINCP'] = pums_hh.HINCP * (pums_hh.ADJINC/1000000)
    return pums_hh, pums_person