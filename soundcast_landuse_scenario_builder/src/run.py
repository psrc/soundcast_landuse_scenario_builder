import configuration
from pathlib import Path
import yaml

file = Path().joinpath(configuration.args.configs_dir, "config.yaml")
config = yaml.safe_load(open(file))

print('Done')