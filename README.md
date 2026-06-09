# Soundcast Landuse Scenario Builder

This tool is used to modify Soundcast landuse inputs. Users can specify household totals for target zones and Soundcast-formatted inputs will be produced. Population distributions from Vision 2050 will be applied to all changes, which maintains underlying policy/forecast assumptions while allowing users to change detailed locations of households at a zonal level. This tool parcelizes these changes and updates Soundcast's synthetic population files to allow scenario testing.

PUMS seed records and PUMA geographies are now downloaded automatically from the U.S. Census Bureau at runtime, so users no longer need to supply PUMS data files or a PUMA GIS layer.


## Install and Setup

This project uses the [uv](https://docs.astral.sh/uv/) package manager to manage its Python environment and dependencies.

1. Clone this repository (or download the code) to a working directory.
2. [Install uv](https://docs.astral.sh/uv/getting-started/installation/) if it is not already available on your machine.
3. From the repository root, create the environment and install all dependencies (including PopulationSim) with:

       uv sync

   This reads `pyproject.toml` and creates a `.venv` in the repository root with everything required to run the tool.

You can run any command inside the managed environment by prefixing it with `uv run`, so there is no separate environment to activate manually.


## Inputs

The tool requires a small set of local inputs. [Users can download example input data here](https://file.ac/zMj1JWnmnGg/). Unzip these folders to a convenient location on your local machine. For example purposes, we will assume the data has been extracted to `C:\users\test\landuse_scenario_test`. The paths below are then specified in **config.yaml** for your run.

PUMS household/person seed records and the matching PUMA boundaries are downloaded automatically based on the `pums_year` setting, so they do **not** need to be provided as inputs.

### Configuring Inputs
The example configuration lives in [examples/psrc_sub_area/config.yaml](examples/psrc_sub_area/config.yaml). Copy or edit this file for your own run and update the following input locations.

- **input_land_use_path**
  - Soundcast parcel and synthetic population files.
     - The parcel file (parcels_urbansim.txt) will be used to allocate households from TAZ-level controls to parcels. The parcel file used here will determine the spatial detail of any changes to land use at a zone level and will ensure results are based on some desired distribution. For instance, using a 2050 parcel file with PSRC's Vision 2050 policies will ensure that households and jobs are distributed across zones with this same policy reference, even with changes in zone-level totals.
     - If the tool is being run for only a portion of the region (a specific study area), the synthetic household and persons data (hh_and_persons.h5) will be updated with any changes, leaving all other households and persons the same. The user must specify this with the variable **update_existing_h5**. When True, the data from this input hh_and_persons.h5 will be copied and updated where appropriate. When False, an entirely new synthetic population file will be generated, which should only be done when performing a regional-scale analysis.
- **input_gis_data_path**
  - A geodatabase (`.gdb`) or shapefile directory that contains the study area TAZ layer named by the **taz_layer** setting (the example uses `study_area_taz`). This layer defines the zones included in the analysis. The PUMA layer is no longer required here — it is downloaded automatically.
- **input_pums_data_path**
  - A local directory used as the download/cache location for the PUMS seed files. The tool downloads the PUMS data here automatically; you do not need to place any files in it. Control the download with:
    - **pums_year**: the PUMS 5-Year vintage to download (e.g. `2021`).
    - **pums_overwrite**: set to `True` to force a fresh re-download, or `False` to reuse previously downloaded files.

For the example data, these should be set as follows (updating to your local data directory where appropriate):
- input_land_use_path: `C:\users\test\landuse_scenario_test\land_use\2050`
- input_gis_data_path: `C:\users\test\landuse_scenario_test\gis_data.gdb`
- input_pums_data_path: `C:\users\test\landuse_scenario_test\pums_data` (download target; created automatically if it does not exist)

File names for the land use inputs should not be changed for the example data, but users are welcome to change these via the `parcel_file` and `synthetic_pop_file` settings as needed.

Make sure to update the **output_dir** field to a convenient location on your machine. This will be the location where PopulationSim inputs and outputs of the tool are created. Note that this directory will be overwritten when the tool is run.

As mentioned above, set **update_existing_h5** to True for the example, which will use the supplied synthetic population file (hh_and_persons.h5), located in the input_land_use_path, as the basis for editing population for a study area. In general, this variable should be True for any study area analysis and False only when running for the full region.

Users can turn off some portions of the tool to only allocate jobs, households, persons (or any combination of those) with the following settings. These should be kept as True for the example:
- update_jobs
- update_hh
- update_persons

Finally, column names can be changed if required for other data sets, but these should generally remain unchanged.

Note that in the [provided example data](https://file.ac/zMj1JWnmnGg/) the land_use folder contains a "2050" sub-directory. This designates this data as 2050. Users can add additional years or scenarios here and should update the config setting "input_land_use_path" to the full path of the desired directory.


## Running the Tool

The full pipeline is run through the command line interface. The CLI is installed as part of `uv sync` and is invoked with the `run` subcommand, pointing the `-c`/`--configs_dir` option at the directory that contains your `config.yaml` (along with `controls.csv` and `populationsim_settings.yaml`).

To run the included example:

    uv run soundcast_landuse_scenario_builder run -c examples/psrc_sub_area

A single `run` performs the complete pipeline end to end:

1. **Generate controls** — Based on the study area zones in the GIS layer, a set of PopulationSim control files and other inputs are produced. PUMS seed records and PUMA geographies are downloaded automatically, and seed records are selected from the study area to produce the refined synthetic populations.
2. **Allocate households** — PopulationSim is run with the generated controls to produce synthetic household and person records for the study area. These synthetic data replace the existing household and person data for the affected zones and are written out as updated Soundcast inputs.

All artifacts are written to the location specified in `output_dir` in your config:

- **configs**: files used internally by PopulationSim.
- **data**: PopulationSim inputs, including:
    - **user_allocation.csv**: the primary file describing total households and jobs by zone. This is the main control for scenario building — change totals only for the zones you wish to update. The list of zones is built from the study area defined in the input GIS layer.
    - **future_controls.csv**: a detailed file describing zone-level control totals for PopulationSim. Household and person totals here are derived from user_allocation.csv; advanced users can adjust additional distributions in this file, but any household/person totals will be superseded by the values in user_allocation.csv.
- **output**: the final outputs of PopulationSim and this tool:
    - **parcels_urbansim.txt**: Soundcast parcel-level landuse file, updated for total number of households per parcel.
    - **hh_and_persons.h5**: Soundcast synthetic household and person data, updated to reflect the land use changes.

To build a scenario, edit the zone totals in **user_allocation.csv** for the zones you want to change, then re-run the pipeline to regenerate the Soundcast inputs that reflect those edits.

You can view the available CLI options at any time with:

    uv run soundcast_landuse_scenario_builder --help 
    
