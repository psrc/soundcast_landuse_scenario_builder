from pathlib import Path
import yaml
import argparse
import sys
from soundcast_landuse_scenario_builder.utils.validate_settings import ValidateSettings
import soundcast_landuse_scenario_builder.src.generate_controls
import soundcast_landuse_scenario_builder.src.allocate_hh


# file = Path().joinpath(configuration.args.configs_dir, "config.yaml")
# config = yaml.safe_load(open(file))

def add_run_args(parser, multiprocess=True):
    """
    Run command args
    """
    parser.add_argument(
        "-c",
        "--configs_dir",
        type=str,
        metavar="PATH",
        help="path to configs dir",
    )

def run(args):
    config = yaml.safe_load(open(Path(f"{args.configs_dir}/config.yaml")))
    config['configs_dir'] = args.configs_dir
    config = ValidateSettings(**config)
    if config.run_generate_controls:
        soundcast_landuse_scenario_builder.src.generate_controls.run(config, args)
    if config.run_allocate_hh:
        soundcast_landuse_scenario_builder.src.allocate_hh.run(config)
    print('Done')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_run_args(parser)
    args = parser.parse_args()
    sys.exit(run(args))