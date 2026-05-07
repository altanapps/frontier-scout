from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Lab:
    name: str
    people_url: str
    arxiv_categories: list[str] = field(default_factory=list)


def load(path: Path) -> list[Lab]:
    data = yaml.safe_load(path.read_text())
    return [Lab(**lab) for lab in data.get("labs", [])]


EXAMPLE = """\
# frontier-scout config — edit to taste, then run `frontier-scout roster`.
# arxiv_categories is optional; restricts paper search to those categories.
# https://arxiv.org/category_taxonomy

labs:
  - name: ETH Zurich — Robotic Systems Lab
    people_url: https://rsl.ethz.ch/people.html
    arxiv_categories: [cs.RO, cs.LG]

  - name: Imperial College — Hamlyn Centre
    people_url: https://www.imperial.ac.uk/hamlyn-centre/people/
    arxiv_categories: [cs.RO]

  - name: Oxford Robotics Institute
    people_url: https://ori.ox.ac.uk/people/
    arxiv_categories: [cs.RO]
"""


def write_example(path: Path) -> None:
    path.write_text(EXAMPLE)
