"""
* Render Spec Module
* Handles parsing render spec file, aka yaml files that contain a set of configurations and cards to render
"""

import os
import re
import glob
from pathlib import Path
from typing import Dict, TypedDict
from dataclasses import dataclass

from pydantic import BaseModel, RootModel

from src.cards import CardDetails, parse_card_info
from src.utils.data_structures import parse_model

# region Model-Types


class ConfigModel(BaseModel):
    name: str
    settings: list[str] | str


class FileModel(BaseModel):
    file: str
    settings: list[str] | str = []


class GroupModel(BaseModel):
    files: list[FileModel | str] | FileModel | str
    groups: list[GroupModel] | GroupModel = []
    settings: list[str] | str = []


class RenderSpecModel(BaseModel):
    files: list[FileModel | str] | FileModel | str = []
    groups: list[GroupModel] | GroupModel = []
    configs: list[ConfigModel] | ConfigModel = []


# endregion Model-Types
# region Types


@dataclass
class RenderConfiguration:
    name: str
    spec: str


@dataclass
class CardSpec:
    spec: str
    actual_path: Path | None


class RenderSpec(TypedDict):
    """Render spec obtained from parsing the file."""

    name: str
    file: Path
    configs: Dict[str, RenderConfiguration]
    cards: list[CardDetails]


# endregion Types

# region Parsing


def parse_render_spec_file(render_spec_path: Path) -> RenderSpecModel:
    return parse_model(render_spec_path, RootModel[RenderSpecModel]).root


def parse_render_spec(render_spec_path: Path) -> RenderSpec:
    """Retrieve render spec from the input file.

    Args:
        render_spec_path: Path to the yaml file.

    Returns:
        Dict containing the configurations and cards in this spec.
    """

    render_spec_data = parse_render_spec_file(render_spec_path)

    def as_list[T](values: list[T] | T) -> list[T]:
        if isinstance(values, list):
            return values  # type: ignore
        return [values]

    def join_settings(settings: list[str] | str) -> str:
        if isinstance(settings, str):
            return settings
        return " ".join(settings)

    configs = {
        c.name: RenderConfiguration(c.name, join_settings(c.settings))
        for c in as_list(render_spec_data.configs)
    }

    render_spec_name = render_spec_path.stem
    parent_dir = render_spec_path.parent

    cards: list[CardDetails] = []

    def resolve_file(file: str) -> list[CardSpec]:
        if "*" in file:
            specs = glob.glob(file, root_dir=parent_dir, recursive=True)
            return [
                CardSpec(s.split(".")[0], parent_dir / s)
                for s in specs
                if not s.endswith(".yaml") and not s.endswith(".yml")
            ]
        else:
            abs_file = render_spec_path.parent / Path(file)
            if os.path.exists(abs_file):
                return [CardSpec(file.split(".")[0], abs_file)]
            else:
                return [CardSpec(file, None)]

    def append_card(card_spec: CardSpec):
        spec = card_spec.spec

        # Make sure the extension doesn't contain a ']' as that implies
        # we have something without extension using a config that contains
        # something with extension, e.g. [art=file.png]
        if not re.match(r"\.[^\]]+$", spec):
            spec += ".png"

        # Pretend this is a file right next to the spec and parse that
        full_card_path = parent_dir / Path(spec).name
        card_info = parse_card_info(full_card_path)

        path = card_spec.actual_path
        if path is not None:
            if "art" not in card_info["kwargs"]:
                card_info["kwargs"]["art"] = str(path)
            if "dir" not in card_info["kwargs"]:
                if parent_dir in path.parents:
                    rel_dir = path.relative_to(parent_dir).parent
                    card_info["kwargs"]["dir"] = str(rel_dir)

        cards.append(card_info)

    def append_configs(card: CardSpec, card_configs: list[str]) -> CardSpec:
        resolved_configs = [
            configs[c].spec if c in configs else c for c in card_configs
        ]
        config = " ".join(resolved_configs)
        return CardSpec(
            f"{card.spec} {config}",
            card.actual_path,
        )

    def parse_group(group: GroupModel, root_group: bool = True) -> list[CardSpec]:
        group_cards: list[CardSpec] = []
        group_settings = as_list(group.settings)

        for file_model in as_list(group.files):
            if isinstance(file_model, FileModel):
                file = file_model.file
                settings = as_list(file_model.settings) + group_settings
            else:
                file = file_model
                settings = group_settings

            for card_spec in resolve_file(file):
                card_spec = append_configs(card_spec, settings)
                group_cards.append(card_spec)

        for nested_group in as_list(group.groups):
            for card_spec in parse_group(nested_group):
                card_spec = append_configs(card_spec, group_settings)
                group_cards.append(card_spec)

        def expand_variable(card: CardSpec, variable: str, value: str | int):
            return CardSpec(
                card.spec.replace(variable, str(value)),
                card.actual_path,
            )

        group_cards = [
            expand_variable(c, "${GROUP_INDEX}", i) for (i, c) in enumerate(group_cards)
        ]
        if root_group:
            group_cards = [
                expand_variable(c, "${ROOT_GROUP_INDEX}", i)
                for (i, c) in enumerate(group_cards)
            ]

        return group_cards

    for card_model in as_list(render_spec_data.files):
        if isinstance(card_model, str):
            card = FileModel(file=card_model, settings=[])
        else:
            card = card_model

        for card_spec in resolve_file(card.file):
            card_spec = append_configs(card_spec, as_list(card.settings))
            append_card(card_spec)

    for group in as_list(render_spec_data.groups):
        for card_spec in parse_group(group):
            append_card(card_spec)

    return {
        "name": render_spec_name,
        "file": render_spec_path,
        "configs": configs,
        "cards": cards,
    }


# endregion Parsing
