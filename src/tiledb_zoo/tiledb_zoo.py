import asyncio
from pathlib import Path
from typing import Optional
import logging
import sys
import os

import yaml

DEFAULT_CONFIG_NAME = "default_config.yml"

class FeedstockProject:
    def __init__(self, name: str, project_config: dict, output_dir: Path):
        self.name = name
        self.url = project_config["url"]
        self.ref = project_config["ref"]
        self.output_dir = output_dir
        self.depends = project_config.get("depends", None)
        self.variants = project_config.get("variants", None)

        # TODO: Take this as arg
        self.env = {
            "CPU_COUNT": str(os.cpu_count())
        }
        logging.info(f"Using environment variables: {self.env}")

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
                logging.info(f"Downloading {self.name} finished")

                if proc.returncode != 0:
                    logging.error(f"{self.name} download failed with exit code: {proc.returncode}")

                return proc.returncode

    async def build(self):
        logging.info(f"Building {self.name}")

        command = [
            sys.executable, "-m", "conda", "build", ".", "--use-local"
        ]

        if self.variants:
            command.append("--variants")
            command.append(yaml.dump(self.variants))

        logging.info(command)

        with open(self.output_dir / f"{self.name}_build_out.txt", "w") as outfile:
            with open(self.output_dir / f"{self.name}_build_err.txt", "w") as errfile:
                proc = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=outfile,
                    stderr=errfile,
                    cwd=self.output_dir / self.name,
                    env=self.env.update(os.environ)
                )

                await proc.communicate()
                logging.info(f"Building {self.name} finished")

                if proc.returncode != 0:
                    logging.error(f"{self.name} build failed with exit code: {proc.returncode}")

                return proc.returncode


def resolve_dependencies(projects: list[FeedstockProject]) -> list[list[FeedstockProject]]:
    # NOTE: There must be a better way to do this, but for our 3 level dependencies this is fine
    result = [[project for project in projects if project.depends is None]]

    if not result:
        raise AttributeError("No projects without dependencies found")

    # NOTE: This is not really optimal
    while True:
        current_layer = []
        for project in projects:
            flat = [p for layer in result for p in layer]
            if project.depends in [p.name for p in flat] and project not in flat:
                current_layer.append(project)

        if current_layer:
            result.append(current_layer)
        else:
            break

    return result


def load_config(path: Optional[Path]) -> dict:
    default_config_path = Path(__file__).parent / DEFAULT_CONFIG_NAME

    with open(default_config_path, "r") as file:
        result = yaml.safe_load(file)

    if path:
        with open(path, "r") as file:
            result = result | yaml.safe_load(file)

    return result


async def build_projects(config: dict):
    logging.info("Start build projects")

    output_dir = Path("build")
    output_dir.mkdir(exist_ok = True)

    projects = [
        FeedstockProject(name, config, output_dir)
            for name, config in config["projects"].items()
    ]

    logging.info("Downloading all projects")
    if not all(ec == 0 for ec in await asyncio.gather(*[project.download() for project in projects])):
        logging.error("One of the download commands failed")
        return

    layers = resolve_dependencies(projects)
    logging.info(f"Building in {len(layers)} layers")

    for layer in layers:
        logging.info(f"Building layer {[p.name for p in layer]}")

        if not all(ec == 0 for ec in await asyncio.gather(*[project.build() for project in layer])):
            logging.error("One of the build commands failed")
            return

    logging.info("Finished")
