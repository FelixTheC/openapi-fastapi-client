import re
from string import Template


def operation_id_to_function_name(operation_id: str) -> str:
    try:
        camel_idx = re.search(r"[A-Z]", operation_id).start()
    except AttributeError:
        return operation_id
    chars = [obj for obj in operation_id]
    chars[camel_idx] = f"_{operation_id[camel_idx].lower()}"
    return operation_id_to_function_name("".join(chars))


def function_like_name_to_class_name(val: str, /):
    def to_title(val_: str):
        if val_[0].isupper():
            return val_
        else:
            return val_.title()

    return "".join([to_title(obj) for obj in val.split("_")])


TYPE_CONVERTION = {
    "integer": "int",
    "number": "float",
    "string": "str",
    "object": "dict",
    "array": "list",
    "boolean": "bool",
}

STR_FORMAT = {
    "date": "date",
    "date-time": "datetime",
    "byte": "bytes",
}


def string_constraints(type_info: dict) -> str:
    params = []

    if min_ := type_info.get("min_length"):
        params.append(f"min_length={min_}")
    if max_ := type_info.get("maxLength"):
        params.append(f"max_length={max_}")

    if params:
        return ",".join(params)
    return ""


def number_constraints(type_info: dict) -> str:
    params = []
    if min_ := type_info.get("minimum"):
        modifier = "gt" if type_info.get("exclusiveMinimum", True) else "ge"
        params.append(f"{modifier}={min_}")
    if max_ := type_info.get("maximum"):
        modifier = "lt" if type_info.get("exclusiveMaximum", True) else "le"
        params.append(f"{modifier}={max_}")
    if multiple_of := type_info.get("multipleOf"):
        params.append(f"multiple_of={multiple_of}")

    if params:
        return ",".join(params)
    return ""


def create_validator(field_name: str, field_type: str):
    function_name = f"optional_{field_name}"
    return Template(
        """
    @validator("$field_name")
    def $function_name(cls, val: $field_type):
        if val is not None:
            return val
        else:
            raise ValueError("$field_name may not be None")
        """
    ).substitute(field_name=field_name, function_name=function_name, field_type=field_type)


if __name__ == "__main__":
    print(function_like_name_to_class_name("salutation"))
