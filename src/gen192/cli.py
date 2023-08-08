import os
import pathlib as pl
import hashlib
from contextlib import contextmanager
from glob import glob
import yaml
from dataclasses import dataclass


PIPELINE_NAMES = {
    'ABCD': 'cpac_abcd-options',
    'CCS': 'cpac_ccs-options',
    'RBC': 'RBCv0',
    'fMRIPrep': 'cpac_fmriprep-options',
}


@contextmanager
def cd(path):
    """Context manager for changing the working directory"""
    old_wd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old_wd)


def download_cpac_configs(checkout_sha: str, dir_configs: pl.Path):
    print(f'Check out C-PAC ({checkout_sha}) from github...')
    print(f'-------------------------------------------')
    os.system('git clone https://github.com/FCP-INDI/C-PAC.git dist/temp_cpac')
    with cd('dist/temp_cpac'):
        if os.system(f'git checkout "{checkout_sha}"') != 0:
            print(f'Could not checkout {checkout_sha}')
            exit(1)
    print(f'-------------------------------------------')

    print(f'Extracting configs...')
    os.system(f'cp -r dist/temp_cpac/CPAC/resources/configs {dir_configs}')

    print(f'Removing C-PAC...')
    os.system('rm -rf dist/temp_cpac')


@dataclass
class PipelineConfig:
    name: str
    file: pl.Path
    config: dict


def main(checkout_sha = '89160708710aa6765479949edaca1fe18e4f65e3'):

    cpac_version_hash = hashlib.sha1(f'{checkout_sha}'.encode()).hexdigest()

    dir_dist = pl.Path('dist')
    dir_dist.mkdir(parents=True, exist_ok=True)
    dir_configs = dir_dist / f'configs_{cpac_version_hash}'

    # Download C-PAC configs
    if not dir_configs.exists():
        download_cpac_configs(checkout_sha, dir_configs)

    # Load pipeline YAMLS
    configs = {}
    for pipeline_config_file in dir_configs.glob(f'pipeline_config_*.yml'):
        with open(pipeline_config_file, 'r') as handle:
            pipeline_config = yaml.safe_load(handle)
            pipeline_name = pipeline_config['pipeline_setup']['pipeline_name']

            while pipeline_name in configs:
                print(f'WARNING: Duplicate pipeline name: {pipeline_name}: {pipeline_config_file} - {configs[pipeline_name].file}')
                pipeline_name += '_dup'

            configs[pipeline_name] = PipelineConfig(
                name=pipeline_config['pipeline_setup']['pipeline_name'],
                file=pipeline_config_file,
                config=pipeline_config
            )
    
    # Check that all pipelines are present
    for pipeline_label, pipeline_id in PIPELINE_NAMES.items():
        if not pipeline_id in configs:
            print(f'ERROR: Could not find pipeline {pipeline_label}')
            exit(1)


if __name__ == '__main__':
    main()