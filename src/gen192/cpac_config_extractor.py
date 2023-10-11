import os
import pathlib as pl
import sys

from .utils import cd, filesafe


def _download_cpac_repo(cpac_dir: pl.Path, checkout_sha: str):
    """Downloads C-PAC configs from github and extracts them to the specified directory"""

    print(f"Check out C-PAC ({checkout_sha}) from github...")
    print(f"-------------------------------------------")
    os.system(f"git clone https://github.com/FCP-INDI/C-PAC.git {cpac_dir}")
    with cd(cpac_dir):
        if os.system(f'git checkout "{checkout_sha}"') != 0:
            print(f"Could not checkout {checkout_sha}")
            exit(1)
    print(f"-------------------------------------------")


def fetch_and_expand_cpac_configs(
    cpac_dir: pl.Path,
    output_dir: pl.Path,
    checkout_sha: str,
    config_names_ids: dict[str, str],
):
    """
    Fetches C-PAC configs from github, fully expands them (FROM: parent),
    and then saves them to the specified directory.
    """
    if not (cpac_dir / "CPAC").exists():
        cpac_dir.mkdir(parents=True, exist_ok=True)
        _download_cpac_repo(cpac_dir=cpac_dir, checkout_sha=checkout_sha)

    output_dir.mkdir(parents=True, exist_ok=True)

    cpac_module_path = str(cpac_dir.absolute())

    if cpac_module_path not in sys.path:
        sys.path.append(cpac_module_path)

    from CPAC.utils.configuration.configuration import Preconfiguration  # noqa
    from CPAC.utils.configuration.yaml_template import \
        create_yaml_from_template  # noqa

    for config_name, config_id in config_names_ids.items():
        conf = Preconfiguration(config_id)
        config_yaml_string = create_yaml_from_template(conf.dict(), "blank")

        with open(
            output_dir / (filesafe(config_name) + ".yml"), "w", encoding="utf-8"
        ) as handle:
            handle.write(config_yaml_string)
