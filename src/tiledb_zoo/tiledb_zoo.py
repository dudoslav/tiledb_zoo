import asyncio
from pathlib import Path
from typing import Optional
import logging

import yaml

DEFAULT_CONFIG_NAME = "default_config.yml"

class FeedstockProject:
    def __init__(self, name: str, project_config: dict, output_dir: Path):
        self.name = name
        self.url = project_config["url"]
        self.ref = project_config["ref"]
        self.config = project_config["config"]
        self.output_dir = output_dir

    async def download(self):
        logging.info(f"Downloading {self.name}")

        with open(self.output_dir / f"{self.name}_download_out.txt", "w") as outfile:
            with open(self.output_dir / f"{self.name}_download_err.txt", "w") as errfile:
                proc = await asyncio.create_subprocess_shell(
                     f"git clone {self.url} {self.output_dir / self.name}",
                    stdout=outfile,
                    stderr=errfile
                )

                await proc.communicate()
                return proc.returncode

    async def build(self):
        logging.info(f"Building {self.name}")

        with open(self.output_dir / f"{self.name}_build_out.txt", "w") as outfile:
            with open(self.output_dir / f"{self.name}_build_err.txt", "w") as errfile:
                proc = await asyncio.create_subprocess_shell(
                     f"python build-locally.py {self.config}",
                    stdout=outfile,
                    stderr=errfile,
                    cwd=self.output_dir / self.name
                )

                await proc.communicate()
                return proc.returncode

def load_config(path: Optional[Path]) -> dict:
    default_config_path = Path(__file__).parent / DEFAULT_CONFIG_NAME

    with open(default_config_path, "r") as file:
        result = yaml.safe_load(file)

    if path:
        with open(path, "r") as file:
            result = result | yaml.safe_load(file)

    return result


async def build_projects(config: dict):
    output_dir = (Path("build"))
    output_dir.mkdir(exist_ok = True)

    projects = [
        FeedstockProject(name, config, output_dir)
            for name, config in config["projects"].items()
    ]

    if not all(ec == 0 for ec in await asyncio.gather(*[project.download() for project in projects])):
        logging.error("One of the download commands failed")
        return

    if not all(ec == 0 for ec in await asyncio.gather(*[project.build() for project in projects])):
        logging.error("One of the build commands failed")
        return
