import argparse
import copy
import json
import pathlib as pl
import shutil
from dataclasses import dataclass
from typing import Any, Dict, Generator, List

import yaml

from .config import CPAC_SHA
from .cpac_config_extractor import check_cpac_config, fetch_and_expand_cpac_configs
from .utils import (
    aslist,
    b64_urlsafe_hash,
    filesafe,
    multi_del,
    multi_get,
    multi_set,
    print_warning,
)

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
        name="Functional Masking",
        merge_paths=[
            ["functional_preproc", "func_masking"],
            [
                "registration_workflows",
                "anatomical_registration",
                "T1w_brain_template_mask",
            ],
            [
                "registration_workflows",
                "functional_registration",
                "func_registration_to_template",
                "target_template",
                "T1_template",
                "T1w_brain_template_mask_funcreg",
            ],
        ],
    ),
    PipelineStep(
        name="Functional Registration",
        merge_paths=[
            ["registration_workflows", "functional_registration", "coregistration"],
        ],
    ),
]
"""Pipeline steps and their paths in the C-PAC config to include in the generation."""


@dataclass
class PipelineConfig:
    """Represents a C-PAC pipeline configuration"""

    name: str
    file: pl.Path
    config: dict
    notes: str | None = None

    def clone(self) -> "PipelineConfig":
        return PipelineConfig(name=self.name, file=self.file, config=copy.deepcopy(self.config))

    def set_name(self, name: str) -> None:
        self.name = name
        self.config["pipeline_setup"]["pipeline_name"] = name

    def _file_exists(self) -> bool:
        return self.file.exists()

    def dump(self, exist_ok: bool = False) -> None:
        if self._file_exists() and not exist_ok:
            raise FileExistsError(f"File {self.file} already exists")
        with open(self.file, "w") as handle:
            yaml.dump(self.config, handle)
        if self.notes is not None:
            with open(self.file.with_suffix(".notes.txt"), "w") as handle:
                handle.write(self.notes)


@dataclass
class PipelineCombination:
    """Represents a combination of all parameters pipeline generation should be run for"""

    pipeline_id: str
    pipeline_perturb_id: str
    step: PipelineStep
    # connectivity_method: str
    # use_nuisance_correction: bool

    def name(self, pipeline_num: int) -> str:
        return (
            f"p{pipeline_num:03d}_"
            f"base-{filesafe(self.pipeline_id)}_"
            f"perturb-{filesafe(self.pipeline_perturb_id)}_"
            f"step-{filesafe(self.step.name)}_"
            # f"conn-{filesafe(self.connectivity_method)}_"
            # f"nuisance-{filesafe(str(self.use_nuisance_correction))}"
        )

    def filename(self, pipeline_num: int) -> str:
        return self.name(pipeline_num) + ".yml"


def iter_pipeline_combis() -> Generator[PipelineCombination, Any, None]:
    """
    Iterate over all possible parameter combinations.
    """
    for pipeline_id in PIPELINE_NAMES.keys():
        for pipeline_perturb_id in PIPELINE_NAMES.keys():
            for step in PIPELINE_STEPS:
                # for connectivity_method in CONNECTIVITY_METHODS:
                #for nuisance_method in NUISANCE_METHODS:
                yield PipelineCombination(
                    pipeline_id=pipeline_id,
                    pipeline_perturb_id=pipeline_perturb_id,
                    step=step,
                    # connectivity_method=connectivity_method,
                    # use_nuisance_correction=nuisance_method,
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


def _config_deactivate_derivatives(pipeline: PipelineConfig) -> None:
    """Deactivate all derivatives in a pipeline (except connectomes)"""
    run_paths: list[MergePath] = [
        ["amplitude_low_frequency_fluctuation", "run"],
        ["regional_homogeneity", "run"],
        ["voxel_mirrored_homotopic_connectivity", "run"],
        ["network_centrality", "run"],
        ["longitudinal_template_generation", "run"],
        ["post_processing", "spatial_smoothing", "run"],
        ["post_processing", "z-scoring", "run"],
        ["seed_based_correlation_analysis", "run"],
        ["PyPEER", "run"],
    ]

    for run_path in run_paths:
        multi_set(pipeline.config, index=run_path, value=False)


def _config_remove_coregistration_reference(pipeline: PipelineConfig) -> None:
    """Remove coregistration reference entry from a pipeline config"""
    multi_del(
        pipeline.config, index=["registration_workflows", "functional_registration", "coregistration", "reference"]
    )


def generate_pipeline_from_combi(
    pipeline_num: int, combi: PipelineCombination, configs: ConfigLookupTable
) -> PipelineConfig:
    # Copy pipeline
    pipeline = configs[combi.pipeline_id].clone()
    pipeline_perturb = configs[combi.pipeline_perturb_id].clone()

    # Merge perturbation step
    merge_paths_identical = []
    for merge_path in combi.step.merge_paths:
        snippet = multi_get(pipeline_perturb.config, index=merge_path)
        snippet_target = multi_get(pipeline.config, index=merge_path)

        if snippet is None:
            warning = f"Can't find path {merge_path} in {pipeline_perturb.name}"
            pipeline.notes = pipeline.notes + "\n" + warning if pipeline.notes else warning
            print_warning(warning)
            multi_del(pipeline.config, index=merge_path)
            continue

        snippet_json = json.dumps(snippet, sort_keys=True, indent=2)
        snippet_target_json = json.dumps(snippet_target, sort_keys=True, indent=2)

        merge_paths_identical.append(snippet_json == snippet_target_json)
        multi_set(pipeline.config, index=merge_path, value=snippet)

    if all(merge_paths_identical):
        warning = (
            f'"{combi.step.name}" perturbation ({combi.pipeline_perturb_id}) '
            f"is identical to target ({combi.pipeline_id})."
        )
        pipeline.notes = pipeline.notes + "\n" + warning if pipeline.notes else warning
        print_warning(warning)

    # Set connectivity method
    multi_set(
        pipeline.config,
        index=["timeseries_extraction", "run"],
        value=True,
    )
    # multi_set(
    #    pipeline.config,
    #    index=["timeseries_extraction", "connectivity_matrix", "using"],
    #    value=aslist(combi.connectivity_method),
    # )
    multi_set(
        pipeline.config,
        index=["timeseries_extraction", "connectivity_matrix", "measure"],
        value=aslist("Pearson"),
    )

    # Set nuisance method
    # # Using regressors for calculations
    # multi_set(
    #     pipeline.config,
    #     index=["nuisance_corrections", "2-nuisance_regression", "run"],
    #     value=aslist(combi.use_nuisance_correction),
    # )
    # # Generating regressors (opposed to ingressing them)
    # multi_set(
    #     pipeline.config,
    #     index=["nuisance_corrections", "2-nuisance_regression", "create_regressors"],
    #     value=combi.use_nuisance_correction,
    # )

    # Deactivate all other derivatives than connectomes
    _config_deactivate_derivatives(pipeline)

    # Remove coregistration reference
    # Was told by CPAC member to remove it
    # This field will be removed from CPAC in the future
    _config_remove_coregistration_reference(pipeline)

    # Activate Freesurfer ingress
    multi_set(
        pipeline.config,
        index=["surface_analysis", "freesurfer", "ingress_reconall"],
        value=True,
    )

    # Dont run Freesurfer recon_all
    multi_set(
        pipeline.config,
        index=["surface_analysis", "freesurfer", "run_reconall"],
        value=False,
    )

    # Dont run any connectivity stuff
    multi_del(
        pipeline.config,
        index=["timeseries_extraction", "connectivity_matrix"],
    )

    # Hardcode freesurfer ingress dir
    multi_set(
        pipeline.config,
        index=["pipeline_setup", "freesurfer_dir"],
        value="/ocean/projects/med220004p/trogers1/many_pipelines/freesurfer/outputs/ABCD_all_subjects",
    )

    # Set pipeline name
    pipeline.set_name(combi.name(pipeline_num))

    return pipeline


def main(force=False) -> None:
    """Main entry point for the CLI"""

    # Delete build and dist directories if force is True
    if force:
        dir_dist = pl.Path("dist")
        dir_build = pl.Path("build")
        
        if dir_dist.exists():
            print(f"Force option enabled: Removing {dir_dist}")
            shutil.rmtree(dir_dist)
            
        if dir_build.exists():
            print(f"Force option enabled: Removing {dir_build}")
            shutil.rmtree(dir_build)

    checkout_sha = CPAC_SHA
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
    configs: ConfigLookupTable = {}
    for config_name in PIPELINE_NAMES.keys():
        config_path = dir_configs / (filesafe(config_name) + ".yml")
        pipeline = load_pipeline_config(config_path)
        configs[config_name] = pipeline
        print(f"Loaded pipeline {config_name} from {config_path}")

    # Generate "pure" pipelines with derivatives turned off
    dir_gen = dir_build / "gen192_pure"
    dir_gen.mkdir(parents=True, exist_ok=True)

    print(f'Generating base pipeline configs in folder "{dir_gen}"')

    for config_name in PIPELINE_NAMES.keys():
        config = configs[config_name].clone()
        config.file = dir_gen / f"{config_name}.yml"
        config.set_name(config_name)
        _config_deactivate_derivatives(config)
        config.dump(exist_ok=False)
        print(f"> Generated pipeline {config_name}")

    # Generate permuted pipelines
    dir_gen = dir_build / "gen192_nofork"
    dir_gen.mkdir(parents=True, exist_ok=True)

    print(f'Generating 192 permutations in folder "{dir_gen}"')

    for pipeline_num, combi in enumerate(iter_pipeline_combis_no_duplicates()):
        filename = combi.filename(pipeline_num)

        print(f"> Generating {filename}")

        combined = generate_pipeline_from_combi(pipeline_num, combi, configs)

        if (
            combi.pipeline_id == "ABCD"
            and combi.pipeline_perturb_id == "CCS"
            and combi.step.name == "Functional Registration"
        ) or (
            combi.pipeline_id == "CCS"
            and combi.pipeline_perturb_id == "ABCD"
            and combi.step.name == "Functional Masking"
        ):
            # See text related to search term "apply_func_mask_in_native_space: false" in
            # https://docs.google.com/document/d/1WyARU5wkkAd9VrT24Tc7xJWJf7CIGO29PY0IM4tdGgQ/edit?tab=t.0
            # todo: sanity check
            multi_set(
                combined.config,
                index=["functional_preproc", "func_masking", "apply_func_mask_in_native_space"],
                value=True,
            )

        # if (
        #     combi.pipeline_id == "CCS"
        #     and combi.pipeline_perturb_id == "ABCD"
        #     and combi.step.name == "Functional Masking"
        #     #and combi.use_nuisance_correction == True
        # ):
        #     # See text related to search term "use_priors" and "lateral_ventricles_mask" in
        #     # https://docs.google.com/document/d/1WyARU5wkkAd9VrT24Tc7xJWJf7CIGO29PY0IM4tdGgQ/edit?tab=t.0
        #     # todo: sanity check
        #     multi_set(
        #         combined.config,
        #         index=["segmentation", "tissue_segmentation", "FSL-FAST", "use_priors", "run"],
        #         value=False,
        #     )
        #     multi_set(
        #         combined.config,
        #         index=["nuisance_corrections", "2-nuisance_regrtession", "lateral_ventricles_mask"],
        #         value=None,
        #     )

        if (
            combi.pipeline_id == "ABCD"
            and combi.pipeline_perturb_id == "RBC"
            and combi.step.name == "Structural Registration"
        ):
            # See text related to search term "overwrite transform" in
            # https://docs.google.com/document/d/1WyARU5wkkAd9VrT24Tc7xJWJf7CIGO29PY0IM4tdGgQ/edit?tab=t.0
            # todo: sanity check
            multi_set(
                combined.config,
                index=["registration_workflows", "anatomical_registration", "overwrite_transform", "run"],
                value=True,
            )

        if (
            (
                combi.pipeline_id == "ABCD"
                and combi.pipeline_perturb_id == "RBC"
                and combi.step.name == "Functional Registration"
            )
            or (
                combi.pipeline_id == "ABCD"
                and combi.pipeline_perturb_id == "fMRIPrep"
                and combi.step.name == "Functional Registration"
            )
            or (
                combi.pipeline_id == "RBC"
                and combi.pipeline_perturb_id == "ABCD"
                and combi.step.name == "Functional Masking"
            )
        ):
            # See text related to search term "Anatomical_Resampled to CCS_Anatomical_Refined" in
            # https://docs.google.com/document/d/1WyARU5wkkAd9VrT24Tc7xJWJf7CIGO29PY0IM4tdGgQ/edit?tab=t.0
            # todo: sanity check
            multi_set(
                combined.config,
                index=["functional_preproc", "func_masking", "using"],
                value=["CCS_Anatomical_Refined"],  # string list, change from ["Anatomical_Resampled"]
            )

        if (
            combi.pipeline_id == "ABCD"
            and combi.pipeline_perturb_id == "fMRIPrep"
            and combi.step.name == "Structural Registration"
        ) or (
            combi.pipeline_id == "CCS"
            and combi.pipeline_perturb_id == "ABCD"
            and combi.step.name == "Structural Masking"
        ):
            # See text related to search term "registration: using: ANTS" in
            # https://docs.google.com/document/d/1WyARU5wkkAd9VrT24Tc7xJWJf7CIGO29PY0IM4tdGgQ/edit?tab=t.0
            # todo: sanity check
            multi_set(
                combined.config,
                index=["registration_workflows", "anatomical_registration", "registration", "using"],
                value=["FSL"],  # string list, change from ["ANTS"]
            )
            multi_set(
                combined.config,
                index=["registration_workflows", "anatomical_registration", "overwrite_transform", "run"],
                value=True,
            )

        if (
            combi.pipeline_id == "RBC"
            and combi.pipeline_perturb_id == "ABCD"
            and combi.step.name == "Functional Masking"
        ) and (
            combi.pipeline_id == "fMRIPrep"
            and combi.pipeline_perturb_id == "ABCD"
            and combi.step.name == "Structural Masking"
        ):
            # See text related to search term "overwrite transform" in
            # https://docs.google.com/document/d/1WyARU5wkkAd9VrT24Tc7xJWJf7CIGO29PY0IM4tdGgQ/edit?tab=t.0
            # todo: sanity check
            multi_set(
                combined.config,
                index=["registration_workflows", "anatomical_registration", "overwrite_transform", "run"],
                value=True,
            )

        if (
            combi.pipeline_id == "RBC"
            and combi.pipeline_perturb_id == "CCS"
            and combi.step.name == "Structural Registration"
        ):
            # See text related to search term "overwrite transform" in
            # https://docs.google.com/document/d/1WyARU5wkkAd9VrT24Tc7xJWJf7CIGO29PY0IM4tdGgQ/edit?tab=t.0
            # todo: sanity check
            multi_set(
                combined.config,
                index=["registration_workflows", "anatomical_registration", "registration", "using"],
                value=["ANTS"],  # string list, change from ["FSL"]
            )

        if (
            combi.pipeline_id == "fMRIPrep"
            and combi.pipeline_perturb_id == "CCS"
            and combi.step.name == "Structural Registration"
        ) and (
            combi.pipeline_id == "RBC"
            and combi.pipeline_perturb_id == "CCS"
            and combi.step.name == "Structural Registration"
        ):
            multi_del(
                combined.config,
                index=["registration_workflows", "anatomical_registration", "overwrite_transform", "using"],
            )
            multi_set(
                combined.config,
                index=["registration_workflows", "anatomical_registration", "registration", "using"],
                value=["ANTS"],  # string list, change from ["FSL"]
            )

        combined.file = dir_gen / filename

        # Let CPAC check if it is a valid config
        ok, err = check_cpac_config(combined.config)
        if not ok:
            warning = f'CPAC-reported config validation error: "{err}"'
            combined.notes = combined.notes + "\n" + warning if combined.notes else warning
            print_warning(warning)

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


def cli():
    parser = argparse.ArgumentParser(description="Your script description")
    parser.add_argument("-f", "--force", action="store_true", help="Force execution without prompts")
    args = parser.parse_args()
    
    main(force=args.force)


if __name__ == "__main__":
    cli()