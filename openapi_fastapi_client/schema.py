from operator import itemgetter
from pathlib import Path
from string import Template
from typing import Optional, TypedDict

import isort

from openapi_fastapi_client.helpers import (
    STR_FORMAT,
    TYPE_CONVERTION,
    create_validator,
    function_like_name_to_class_name,
    number_constraints,
    string_constraints,
)


class FieldDict(TypedDict):
    is_read_only: Optional[bool]
    is_write_only: Optional[bool]
    field: str
    validation: str


class FieldOnlyDict(TypedDict):
    field: str
    validation: str


class ModelClass:
    name: str
    fields: list[FieldDict]
    standard_only_fields: list[FieldOnlyDict]
    read_only_fields: list[FieldOnlyDict]
    write_only_fields: list[FieldOnlyDict]

    def parse_fields(self):
        for val in self.fields:
            field_dict = {"field": val["field"], "validation": ""}

            if val["is_read_only"]:
                if validation := val["validation"]:
                    field_dict["validation"] = validation
                self.read_only_fields.append(field_dict)

            elif val["is_write_only"]:
                if validation := val["validation"]:
                    field_dict["validation"] = validation
                self.write_only_fields.append(field_dict)
            else:
                if validation := val["validation"]:
                    field_dict["validation"] = validation
                self.standard_only_fields.append(field_dict)

    @property
    def request_name(self) -> Optional[str]:
        if self.read_only_fields:
            return f"{self.name}Request"
        return

    @property
    def response_name(self) -> Optional[str]:
        if self.write_only_fields:
            return f"{self.name}Request"
        return


class Schema:
    __slots__ = (
        "data",
        "components",
        "schema_imports",
        "enums",
        "query_param_schemas",
        "referenced_class",
        "class_names",
    )

    def __init__(self, components: dict):
        self.data = []
        self.components = components
        self.schema_imports = set()
        self.enums = {}
        self.query_param_schemas = []
        self.referenced_class = set()
        self.class_names = {}

    def generate_base_imports(self):
        self.schema_imports.add("from datetime import date, datetime")
        self.schema_imports.add("from typing import Optional")
        self.schema_imports.add("from pydantic import BaseModel")

    def create_enum(self, attr_name: str, enum_values: list):
        enum_name = f"{function_like_name_to_class_name(attr_name)}Enum"
        if enum_name in self.enums.get(enum_name, []):
            return enum_name
        else:
            self.schema_imports.add("from enum import Enum")
            self.enums[enum_name] = {
                "class_name": enum_name,
                "attributes": [f"{obj.upper()} = '{obj}'" for obj in enum_values],
            }
            return enum_name

    def get_reference_info(self, reference: str):
        for key, val in self.components.items():
            if key == reference:
                return {
                    "nullable": val.get("nullable", False),
                    "read_only": val.get("readOnly", False),
                    "write_only": val.get("writeOnly", False),
                }

    def create_attribute(self, class_name: str, component: dict):
        class_name = function_like_name_to_class_name(class_name)
        self.class_names[class_name] = {}

        class_info = {
            "class_name": class_name,
            "attributes": [],
            "validators": [],
            "index": 0 if class_name in self.referenced_class else 10,
            "fields": {},
        }
        for name, type_info in component["properties"].items():
            class_info["fields"][name] = {
                "is_read_only": False,
                "is_write_only": False,
                "field": "",
                "validation": "",
            }
            is_optional = name in component.get("required", [])
            delimiter = ": "
            match type_info.get("type", "reference"):
                case "string":
                    if type_info.get("maxLength") or type_info.get("minLength"):
                        self.schema_imports.add("from pydantic import constr")
                        params = string_constraints(type_info)
                        type_hint = f"constr({params})"
                    else:
                        delimiter = ": "
                        if format_ := type_info.get("format"):
                            type_hint = STR_FORMAT.get(format_, "str")
                        elif enum_ := type_info.get("enum"):
                            enum_name = self.create_enum(f"{class_name}_{name}", enum_)
                            type_hint = enum_name
                        else:
                            type_hint = "str"
                case "integer":
                    if type_info.get("minimum") or type_info.get("maximum"):
                        self.schema_imports.add("from pydantic import conint")
                        params = number_constraints(type_info)
                        type_hint = f"conint({params})"
                    else:
                        delimiter = ": "
                        type_hint = "int"
                case "number":
                    if type_info.get("minimum") or type_info.get("maximum"):
                        self.schema_imports.add("from pydantic import confloat")
                        params = number_constraints(type_info)
                        type_hint = f"confloat({params})"
                    else:
                        delimiter = ": "
                        type_hint = "float"
                case "array":
                    delimiter = ": "
                    if reference := type_info["items"].get("$ref"):
                        ref = function_like_name_to_class_name(reference.split("/")[-1])
                        self.referenced_class.add(ref)
                        class_info["index"] = class_info["index"] + 1
                        type_hint = f"list[{ref}]"
                    else:
                        type_hint = "list"
                case "boolean":
                    delimiter = ": "
                    type_hint = "bool"
                case "reference":
                    delimiter = ": "
                    reference_name = type_info["$ref"].split("/")[-1]
                    ref = function_like_name_to_class_name(reference_name)
                    ref_info = self.get_reference_info(reference_name)
                    self.referenced_class.add(ref)
                    class_info["index"] = class_info["index"] + 1

                    if ref_info["nullable"]:
                        type_hint = f"Optional[{ref}] = None"
                    elif ref_info["read_only"]:
                        class_info["fields"][name]["is_read_only"] = True
                        type_hint = f"Optional[{ref}] = None  # read_only"
                    elif ref_info["write_only"]:
                        class_info["fields"][name]["is_write_only"] = True
                        type_hint = f"Optional[{ref}] = None  # write_only"
                    else:
                        type_hint = ref
                case _:
                    type_hint = None

            if type_hint is not None:
                if (
                    type_info.get("nullable", False)
                    or type_info.get("readOnly", False)
                    or type_info.get("writeOnly", False)
                ):
                    comment = ""
                    if type_info.get("readOnly", False):
                        comment = " # read_only"
                        class_info["fields"][name]["is_read_only"] = True
                    elif type_info.get("writeOnly", False):
                        comment = "  # write_only"
                        class_info["fields"][name]["is_write_only"] = True

                    class_info["attributes"].append(
                        f"{name}{delimiter}Optional[{type_hint}] = None{comment}"
                    )
                    class_info["fields"][name][
                        "field"
                    ] = f"{name}{delimiter}Optional[{type_hint}] = None{comment}"

                    if is_optional:
                        self.schema_imports.add("from pydantic import validator")
                        try:
                            field_type = TYPE_CONVERTION[type_info["type"]]
                        except KeyError:
                            field_type = type_hint
                        class_info["fields"][name]["validation"] = create_validator(
                            name, field_type
                        )
                        class_info["validators"].append(create_validator(name, field_type))

                else:
                    class_info["fields"][name]["field"] = f"{name}{delimiter}{type_hint}"
                    class_info["attributes"].append(f"{name}{delimiter}{type_hint}")
        return class_info

    def generate_schemas(self):
        self.generate_base_imports()
        for key, val in self.components.items():
            self.data.append(self.create_attribute(key, val))
        self.data.sort(key=itemgetter("index"))

    def create_enum_class(self, data: dict):
        params = "\n    ".join(data["attributes"])
        return Template(
            """class $class_name(Enum):
    $params
        """
        ).substitute(class_name=data["class_name"], params=params)

    def create_schema_class(self, data: dict):

        standard_fields = []
        standard_fields_validators = []
        read_only_fields = []
        read_only_fields_validators = []
        write_only_fields = []
        write_only_fields_validators = []

        for val in data["fields"].values():
            if val["is_read_only"]:
                read_only_fields.append(val["field"])
                if validation := val["validation"]:
                    read_only_fields_validators.append(validation)
            elif val["is_write_only"]:
                write_only_fields.append(val["field"])
                if validation := val["validation"]:
                    write_only_fields_validators.append(validation)
            else:
                standard_fields.append(val["field"])
                if validation := val["validation"]:
                    standard_fields_validators.append(validation)

        if read_only_fields or write_only_fields:
            tmp = standard_fields + read_only_fields

            read_only_params = "\n    ".join(tmp)
            write_only_params = "\n    ".join(standard_fields + write_only_fields)

            read_only_validators = "\n    ".join(
                standard_fields_validators + read_only_fields_validators
            )
            write_only_validators = "\n    ".join(
                standard_fields_validators + write_only_fields_validators
            )

            return [
                Template(
                    """class $class_name(BaseModel):
    $params

        $validators
            """
                ).substitute(
                    class_name=f'{data["class_name"]}Request',
                    params=write_only_params,
                    validators=write_only_validators,
                ),
                Template(
                    """class $class_name(BaseModel):
    $params

        $validators
            """
                ).substitute(
                    class_name=f'{data["class_name"]}Response',
                    params=read_only_params,
                    validators=read_only_validators,
                ),
            ]
        else:
            params = "\n    ".join(standard_fields)
            validators = "\n".join(standard_fields_validators)
            return [
                Template(
                    """class $class_name(BaseModel):
    $params
        
        $validators
            """
                ).substitute(class_name=data["class_name"], params=params, validators=validators),
            ]

    def write_to_file(self, folder_path: Path, additional_data: list[str] = None):
        data = []
        data.extend(self.schema_imports)
        data.append("\n")
        if additional_data:
            data.extend(additional_data)
            data.append("\n")
        data.extend([self.create_enum_class(obj) for obj in self.enums.values()])
        data.append("\n")
        for obj in self.data:
            data.extend(self.create_schema_class(obj))
        text = "\n".join(data)  # black.format_str("\n".join(data), mode=black.Mode())

        schema_file = folder_path / Path("schema.py")
        with schema_file as file:
            file.write_text(text)
            isort.api.sort_file(file)
