import sys
from soundcast_landuse_scenario_builder.cli import CLI
from soundcast_landuse_scenario_builder.cli import run
#from network_builder.cli import build_transit_segments_parallel

from soundcast_landuse_scenario_builder import __version__, __doc__


def main():
    build_scenario = CLI(version=__version__, description=__doc__)
    build_scenario.add_subcommand(
        name="run",
        args_func=run.add_run_args,
        exec_func=run.run,
        description=run.run.__doc__,
    )

    sys.exit(build_scenario.execute())

if __name__ == "__main__":
    main()