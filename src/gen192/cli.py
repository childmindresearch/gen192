import base64
import copy
import hashlib
import json
import pathlib as pl
import shutil
from dataclasses import dataclass
from typing import Any, Dict, Generator, Iterable, List, Optional, Sequence

import yaml

from .cpac_config_extractor import fetch_and_expand_cpac_configs
from .utils import filesafe

PIPELINE_NAMES = {
    "ABCD": "abcd-options",
    "CCS": "ccs-options",
    "RBC": "rbc-options",
    "fMRIPrep": "fmriprep-options",
}
"""Maps pipeline names to pipeline IDs for all pipelines that should be included in the generation."""

CONNECTIVITY_METHODS = ["AFNI", "Nilearn"]
"""Connectivity methods to include in the generation."""

NUISANCE_METHODS = [True, False]
"""Nuisance methods to include in the generation."""


MergePath = List[str]
"""A path in the C-PAC config (to merge from a perturbed pipeline)"""


@dataclass
class PipelineStep:
    """Represents a pipeline step that should be merged from a perturbed pipeline"""

    name: str
    merge_paths: List[MergePath]


PIPELINE_STEPS: List[PipelineStep] = [
    PipelineStep(name="Structural Masking", merge_paths=[["anatomical_preproc"]]),
    PipelineStep(
        name="Structural Registration",
        merge_paths=[
            ["registration_workflows", "anatomical_registration"],
        ],
    ),
    PipelineStep(
        name="Functional Masking", merge_paths=[["functional_preproc", "func_masking"]]
    ),
    PipelineStep(
        name="Functional Registration",
        merge_paths=[
            ["registration_workflows", "functional_registration", "coregistration"],
        ],
    ),
]
"""Pipeline steps and their paths in the C-PAC config to include in the generation."""


# Utilities


@dataclass
class PipelineConfig:
    """Represents a C-PAC pipeline configuration"""

    name: str
    file: pl.Path
    config: dict

    def clone(self) -> "PipelineConfig":
        return PipelineConfig(
            name=self.name, file=self.file, config=copy.deepcopy(self.config)
        )

    def set_name(self, name: str) -> None:
        self.name = name
        self.config["pipeline_setup"]["pipeline_name"] = name

    def dump(self, exist_ok=False) -> None:
        if self.file.exists() and not exist_ok:
            raise FileExistsError(f"File {self.file} already exists")
        with open(self.file, "w") as handle:
            yaml.dump(self.config, handle)


def multi_get(obj: dict, index: Iterable) -> Optional[Any]:
    """
    Gets a value from a nested dictionary.
    Returns None if the path does not exist.
    """
    for i in index:
        if not isinstance(obj, dict) or i not in obj:
            return None
        obj = obj[i]
    return obj


def multi_set(obj: dict, index: Sequence, value: Any) -> bool:
    """
    Sets a value in a nested dictionary.
    Returns True if the path exists or was able to be created
    and the value was set.
    """
    for idx, i in enumerate(index):
        if not isinstance(obj, dict):
            return False

        if idx == len(index) - 1:
            obj[i] = value
            return True

        if i not in obj:
            obj[i] = {}

        obj = obj[i]
    assert False


def multi_del(obj: dict, index: Sequence) -> Optional[Any]:
    """
    Deletes a value from a nested dictionary.
    Returns the value if the path exists and
    the value was deleted.
    """
    for idx, i in enumerate(index):
        if not isinstance(obj, dict):
            return None

        if idx == len(index) - 1:
            if i in obj:
                val = obj[i]
                del obj[i]
                return val
            return None

        if i not in obj:
            return None

        obj = obj[i]
    assert False


def aslist(obj: Any):
    """
    Converts an object to a list. If the object is
    already a list, it is returned as is.
    """
    if isinstance(obj, list):
        return obj
    return [obj]


def b64_urlsafe_hash(s: str):
    """
    Hashes a string and returns a base64 urlsafe encoded version of the hash.
    """
    return (
        base64.urlsafe_b64encode(hashlib.sha1(s.encode()).digest())
        .decode()
        .replace("=", "")
    )


# Generation


@dataclass
class PipelineCombination:
    """Represents a combination of all parameters pipeline generation should be run for"""

    pipeline_id: str
    pipeline_perturb_id: str
    step: PipelineStep
    connectivity_method: str
    use_nuisance_correction: bool

    def name(self, pipeline_num: int) -> str:
        return (
            f"p{pipeline_num:03d}_"
            f"base-{filesafe(self.pipeline_id)}_"
            f"perturb-{filesafe(self.pipeline_perturb_id)}_"
            f"step-{filesafe(self.step.name)}_"
            f"conn-{filesafe(self.connectivity_method)}_"
            f"nuisance-{filesafe(str(self.use_nuisance_correction))}"
        )

    def filename(self, pipeline_num: int) -> str:
        return self.name(pipeline_num) + ".yml"


def iter_pipeline_combis() -> Generator[PipelineCombination, Any, None]:
    """
    Iterate over all possible parameter combinations.

    From the heights of these pyramids, forty centuries look down on us.
    - Napoleon Bonaparte
    """
    for pipeline_id in PIPELINE_NAMES.keys():
        for pipeline_perturb_id in PIPELINE_NAMES.keys():
            for step in PIPELINE_STEPS:
                for connectivity_method in CONNECTIVITY_METHODS:
                    for nuisance_method in NUISANCE_METHODS:
                        yield PipelineCombination(
                            pipeline_id=pipeline_id,
                            pipeline_perturb_id=pipeline_perturb_id,
                            step=step,
                            connectivity_method=connectivity_method,
                            use_nuisance_correction=nuisance_method,
                        )


def iter_pipeline_combis_no_duplicates() -> Generator[PipelineCombination, Any, None]:
    """Iterates over all pipeline combinations that are not duplicates"""
    for combi in iter_pipeline_combis():
        if combi.pipeline_id != combi.pipeline_perturb_id:
            yield combi


def load_pipeline_config(pipeline_config_file: pl.Path) -> PipelineConfig:
    """Loads a pipeline config from a file and returns the pipeline name and config"""
    with open(pipeline_config_file, "r") as handle:
        pipeline_config = yaml.safe_load(handle)
    return PipelineConfig(
        name=pipeline_config["pipeline_setup"]["pipeline_name"],
        file=pipeline_config_file,
        config=pipeline_config,
    )


ConfigLookupTable = Dict[str, PipelineConfig]
"""A dictionary of pipeline name to config"""


def generate_pipeline_from_combi(
    pipeline_num: int, combi: PipelineCombination, configs: ConfigLookupTable
) -> PipelineConfig:
    # Copy pipeline
    pipeline = configs[combi.pipeline_id].clone()
    pipeline_perturb = configs[combi.pipeline_perturb_id].clone()

    # Merge perturbation step
    for merge_path in combi.step.merge_paths:
        snippet = multi_get(pipeline_perturb.config, index=merge_path)
        snippet_target = multi_get(pipeline.config, index=merge_path)

        if snippet is None:
            print(f"WARNING: Cant find path {merge_path} in {pipeline_perturb.name}")
            multi_del(pipeline.config, index=merge_path)
            continue

        snippet_json = json.dumps(snippet, sort_keys=True, indent=2)
        snippet_target_json = json.dumps(snippet_target, sort_keys=True, indent=2)

        if snippet_json == snippet_target_json:
            print(
                f'WARNING: "{combi.step.name}" perturbation ({combi.pipeline_perturb_id}) is identical to target ({combi.pipeline_id}).'
            )

        multi_set(pipeline.config, index=merge_path, value=snippet)

    # Set connectivity method
    multi_set(
        pipeline.config,
        index=["timeseries_extraction", "run"],
        value=True,
    )
    multi_set(
        pipeline.config,
        index=["timeseries_extraction", "connectivity_matrix", "using"],
        value=aslist(combi.connectivity_method),
    )
    multi_set(
        pipeline.config,
        index=["timeseries_extraction", "connectivity_matrix", "measure"],
        value=aslist("Pearson"),
    )

    # Set nuisance method
    multi_set(
        pipeline.config,
        index=["nuisance_corrections", "2-nuisance_regression", "run"],
        value=aslist(combi.use_nuisance_correction),
    )

    # Set pipeline name
    pipeline.set_name(combi.name(pipeline_num))

    return pipeline


def main(checkout_sha="8ebbd4e3e836eb6cdd1c7e7c4ca2f49b0c55cf79"):
    """Main entry point for the CLI"""

    cpac_version_hash = b64_urlsafe_hash(checkout_sha)

    dir_dist = pl.Path("dist")
    dir_build = pl.Path("build")
    dir_temp = pl.Path("temp")
    dir_build.mkdir(parents=True, exist_ok=True)
    dir_temp.mkdir(parents=True, exist_ok=True)
    dir_configs = dir_build / f"cpac_source_configs_{cpac_version_hash}"

    # Download C-PAC configs
    fetch_and_expand_cpac_configs(
        cpac_dir=dir_temp / "cpac_source",
        output_dir=dir_configs,
        checkout_sha=checkout_sha,
        config_names_ids=PIPELINE_NAMES,
    )

    # Load pipeline YAMLS
    configs = {}
    for config_name in PIPELINE_NAMES.keys():
        config_path = dir_configs / (filesafe(config_name) + ".yml")
        pipeline = load_pipeline_config(config_path)
        configs[config_name] = pipeline
        print(f"Loaded pipeline {config_name} from {config_path}")

    # Generate pipelines
    dir_gen = dir_build / "gen192_nofork"
    dir_gen.mkdir(parents=True, exist_ok=True)

    print(f'Generating in folder "{dir_gen}"')

    for pipeline_num, combi in enumerate(iter_pipeline_combis_no_duplicates()):
        filename = combi.filename(pipeline_num)

        print(f"Generating {filename}")

        combined = generate_pipeline_from_combi(pipeline_num, combi, configs)
        combined.file = dir_gen / filename

        # Write pipeline
        combined.dump(exist_ok=False)

    # Zip all folders in build
    for subfolder in dir_build.glob("*"):
        if subfolder.is_dir():
            shutil.make_archive(
                base_name=str(dir_dist / subfolder.name),
                format="zip",
                root_dir=subfolder,
            )


if __name__ == "__main__":
    main()
