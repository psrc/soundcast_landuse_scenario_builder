from pathlib import Path
import yaml
import argparse
import sys
from soundcast_landuse_scenario_builder.utils.validate_settings import ValidateSettings
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
    config = ValidateSettings(**config)
    print('Done')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    add_run_args(parser)
    args = parser.parse_args()
    sys.exit(run(args))