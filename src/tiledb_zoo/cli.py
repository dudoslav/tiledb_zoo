import asyncio
from pathlib import Path
import logging

import click

from tiledb_zoo.tiledb_zoo import load_config, build_projects

@click.command()
@click.option("--config", "-c", help = "Path to configuration file", type = Path)
def cli(config: Path):
    logging.basicConfig(level=logging.DEBUG)
    c = load_config(config)
    asyncio.run(build_projects(c))

if __name__ == '__main__':
    cli()
