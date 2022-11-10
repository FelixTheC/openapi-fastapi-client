from pprint import pprint

from openapi_fastapi_client.helpers import STR_FORMAT
from openapi_fastapi_client.helpers import function_like_name_to_class_name
from openapi_fastapi_client.helpers import number_constraints
from openapi_fastapi_client.helpers import string_constraints


class Schema:
    def __init__(self, components: dict):
        self.data = []
        self.components = components
        self.schema_imports = set()
        self.enums = {}
        self.query_param_schemas = []

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
            self.enums[enum_name] = {"class_name": enum_name, "attributes": [f"{obj} = '{obj}'" for obj in enum_values]}
            return enum_name

    def create_attribute(self, class_name: str, component: dict):
        class_info = {
            "class_name": function_like_name_to_class_name(class_name),
            "attributes": []
        }
        for name, type_info in component["properties"].items():
            is_optional = name in component.get("required", [])
            delimiter = " = "
            match type_info.get("type", "reference"):
                case "string":
                    if type_info.get("maxLength") or type_info.get("minLength"):
                        self.schema_imports.add("from pydantic import constr")
                        params = string_constraints(type_info)
                        type_hint = f'constr({params})'
                    else:
                        delimiter = ": "
                        if format_ := type_info.get("format"):
                            type_hint = STR_FORMAT.get(format_, "str")
                        elif enum_ := type_info.get("enum"):
                            enum_name = self.create_enum(name, enum_)
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
                        type_hint = f"list[{ref}]"
                    else:
                        type_hint = "list"
                case "boolean":
                    delimiter = ": "
                    type_hint = "bool"
                case "reference":
                    delimiter = ": "
                    ref = function_like_name_to_class_name(type_info["$ref"].split("/")[-1])
                    type_hint = ref
                case _:
                    type_hint = None

            if is_optional and type_hint is not None:
                class_info["attributes"].append(f"{name}{delimiter}Optional[{type_hint}]")
            elif not is_optional and type_hint is not None:
                class_info["attributes"].append(f"{name}{delimiter}{type_hint}")
        return class_info

    def generate_schemas(self):
        for key, val in self.components.items():
            self.data.append(self.create_attribute(key, val))
