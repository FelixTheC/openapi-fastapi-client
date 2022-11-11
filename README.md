# Openapi yaml file to FastApi Client
A commandline tool to generate Api `functions` and their required `pydantic Model` Schema from an `openapi.yaml` of version 3

## Installation
```shell
pip install -U git+https://github.com/FelixTheC/openapi-fastapi-client.git@main
```

## Usage
```shell
openapi-fastapi-client ./openapi.yaml ./my-client
```
- this will generate under the folder `my-client` following files
  - `__init__.py` if not exists
  - `api.py` here are all function calls to the external api
  - `schema.py` here are all pydantic Models

## Arguments
- `OPENAPI_FILE  [required]`
- `OUTPUT_PATH   [required]`

## Help
```shell
openapi-fastapi-client --help
```