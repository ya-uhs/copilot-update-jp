import tomllib
from scripts.common import ROOT


def load_config(name):
    with (ROOT / 'config' / f'{name}.toml').open('rb') as handle:
        return tomllib.load(handle)
