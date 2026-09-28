"""Map Orbit component type names to classes for the form builder."""

from __future__ import annotations

from typing import Any

from almasix.orbit.forms import (
    Block,
    Builder,
    Checkbox,
    CheckboxList,
    CodeEditor,
    ColorPicker,
    DatePicker,
    DateTimePicker,
    Field,
    FileUpload,
    Hidden,
    KeyValue,
    MarkdownEditor,
    ModalTableSelect,
    MoneyInput,
    MonthPicker,
    MorphToSelect,
    MultiSelect,
    OneTimeCodeInput,
    Placeholder,
    Radio,
    RelationshipRepeater,
    Repeater,
    RichEditor,
    Select,
    Slider,
    TableSelect,
    TagsInput,
    Textarea,
    TextInput,
    TimePicker,
    Toggle,
    ToggleButtons,
    ViewField,
    WeekPicker,
    YearPicker,
)
from almasix.orbit.schemas import (
    Callout,
    EmptyState,
    Fieldset,
    Flex,
    Grid,
    Group,
    Icon,
    Image,
    Section,
    Split,
    Tabs,
    Text,
    UnorderedList,
    Wizard,
)

FIELD_TYPES: dict[str, type[Any]] = {
    "TextInput": TextInput,
    "Textarea": Textarea,
    "Select": Select,
    "MultiSelect": MultiSelect,
    "Checkbox": Checkbox,
    "Toggle": Toggle,
    "Hidden": Hidden,
    "Placeholder": Placeholder,
    "DatePicker": DatePicker,
    "DateTimePicker": DateTimePicker,
    "TimePicker": TimePicker,
    "WeekPicker": WeekPicker,
    "MonthPicker": MonthPicker,
    "YearPicker": YearPicker,
    "FileUpload": FileUpload,
    "Radio": Radio,
    "CheckboxList": CheckboxList,
    "TagsInput": TagsInput,
    "ColorPicker": ColorPicker,
    "MoneyInput": MoneyInput,
    "RichEditor": RichEditor,
    "MarkdownEditor": MarkdownEditor,
    "CodeEditor": CodeEditor,
    "KeyValue": KeyValue,
    "Repeater": Repeater,
    "Builder": Builder,
    "Block": Block,
    "Slider": Slider,
    "ToggleButtons": ToggleButtons,
    "OneTimeCodeInput": OneTimeCodeInput,
    "ViewField": ViewField,
    "MorphToSelect": MorphToSelect,
    "TableSelect": TableSelect,
    "ModalTableSelect": ModalTableSelect,
    "RelationshipRepeater": RelationshipRepeater,
    "Field": Field,
}

LAYOUT_TYPES: dict[str, type[Any]] = {
    "Grid": Grid,
    "Flex": Flex,
    "Group": Group,
    "Split": Split,
    "Section": Section,
    "Tabs": Tabs,
    "Fieldset": Fieldset,
    "Wizard": Wizard,
    "Callout": Callout,
    "EmptyState": EmptyState,
    "Text": Text,
    "Icon": Icon,
    "Image": Image,
    "UnorderedList": UnorderedList,
}

COMPONENT_TYPES: dict[str, type[Any]] = {**FIELD_TYPES, **LAYOUT_TYPES}

# Palette groups shown in the visual designer.
PALETTE: list[dict[str, Any]] = [
    {
        "label": "Fields",
        "types": sorted(k for k in FIELD_TYPES if k not in {"Field", "Block"}),
    },
    {
        "label": "Layouts",
        "types": sorted(
            k
            for k in LAYOUT_TYPES
            if k not in {"Text", "Icon", "Image", "UnorderedList", "Callout", "EmptyState"}
        ),
    },
    {
        "label": "Primes",
        "types": ["Text", "Icon", "Image", "UnorderedList", "Callout", "EmptyState"],
    },
]


def resolve_type(type_name: str) -> type[Any]:
    try:
        return COMPONENT_TYPES[type_name]
    except KeyError as exc:
        raise KeyError(f"Unknown Orbit form builder type: {type_name}") from exc


def all_type_names() -> list[str]:
    return sorted(COMPONENT_TYPES)
