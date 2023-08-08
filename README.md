# `gen192`

[![Build](https://github.com/cmi-dair/gen192/actions/workflows/test.yaml/badge.svg?branch=main)](https://github.com/cmi-dair/gen192/actions/workflows/test.yaml?query=branch%3Amain)
[![codecov](https://codecov.io/gh/cmi-dair/gen192/branch/main/graph/badge.svg?token=22HWWFWPW5)](https://codecov.io/gh/cmi-dair/gen192)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![L-GPL License](https://img.shields.io/badge/license-L--GPL-blue.svg)](https://github.com/cmi-dair/gen192/blob/main/LICENSE)
[![pages](https://img.shields.io/badge/api-docs-blue)](https://cmi-dair.github.io/gen192)

192 C-PAC pipeline generator.

Pipelines (4):
- ABCD
- CSS
- fMRIPrep
- RBC

Pipeline steps (4):
- Structural
  - Denoising + Brain Extraction
  - Anatomical Registration
- Functional
  - Despiking + BOLD Mask Generation
  - Co-registration

Connectivity Measures (2):
- AFNI
- Nilearn

Nuisance Regression (2):
- ANTS
- No nuisance regression

|   Options | Info                            |
| --------: | ------------------------------- |
|         4 | Pipelines                       |
| &times; 3 | Perturbations (other pipelines) |
| &times; 4 | Pipeline steps                  |
| &times; 2 | Connectivity measures           |
| &times; 2 | Nuisance regressions            |
|     = 192 | Number of pipelines             |


## Installation

Get the newest development version via:

```sh
pip install git+https://github.com/cmi-dair/gen192
```

## Usage

```sh
gen192 --help
```

## Links or References

- [https://www.wikipedia.de](https://www.wikipedia.de)
