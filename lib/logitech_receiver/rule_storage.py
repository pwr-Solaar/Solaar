from pathlib import Path
from typing import Dict

import yaml


class YmlRuleStorage:
    def __init__(self, path: Path):
        self._config_path = path

    def save(self, rules: Dict[str, str]) -> None:
        # This is a trick to show str/float/int lists in-line (inspired by https://stackoverflow.com/a/14001707)
        class inline_list(list):
            pass

        def blockseq_rep(dumper, data):
            return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=True)

        yaml.add_representer(inline_list, blockseq_rep)
        format_settings = {
            "encoding": "utf-8",
            "explicit_start": True,
            "explicit_end": True,
            "default_flow_style": False,
        }
        with open(self._config_path, "w") as f:
            f.write("%YAML 1.3\n")  # Write version manually
            yaml.dump_all(rules, f, **format_settings)

    def load(self) -> list:
        with open(self._config_path) as config_file:
            plain_rules = list(yaml.safe_load_all(config_file))
        return plain_rules


class FakeRuleStorage:
    def __init__(self, rules=None):
        if rules is None:
            self._rules = {}
        else:
            self._rules = rules

    def save(self, rules: dict) -> None:
        self._rules = rules

    def load(self) -> dict:
        return self._rules
