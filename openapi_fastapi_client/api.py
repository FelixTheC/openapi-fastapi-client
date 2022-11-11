from pathlib import Path
from string import Template

import black

from openapi_fastapi_client.helpers import TYPE_CONVERTION
from openapi_fastapi_client.helpers import operation_id_to_function_name


def get_function_info_dict():
    return {
        "url": "",
        "method": "",
        "function_name": "",
        "path_parameters": set(),
        "query_parameters": "",
        "request_obj": "",
        "application_type": "application/json",
        "response_obj": ""
    }


class Api:
    def __init__(self, paths: dict):
        self.data = []
        self.paths = paths
        self.schema_imports = set()
        self.query_param_schemas = []

    def generate_base_imports(self):
        self.data.append("import requests")
        self.data.append("from typing import Any, Optional")

    def get_component_obj_name(self, data: dict) -> str | None:
        if json_body := data["content"].get("application/json"):
            if "items" in json_body["schema"]:
                return json_body["schema"]["items"]["$ref"]
            elif "$ref" in json_body["schema"]:
                return json_body["schema"]["$ref"]
        return None

    def create_query_param_typedict(self, func_name: str, params: set) -> tuple[str, str]:
        cls_name = func_name.title().replace("_", "") + "Query"
        request_str = Template("""class $cls_name(BaseModel):
        $params""")
        return request_str.substitute(cls_name=cls_name, params="\n".join(params)), cls_name

    def generate_obj_imports(self) -> None:
        for level_0 in self.paths.values():
            for val in level_0.values():
                if response := val.get("responses"):
                    for resp_val in response.values():
                        if "content" in resp_val:
                            component_ref = self.get_component_obj_name(resp_val)
                            if component_ref:
                                self.schema_imports.add(component_ref.split("/")[-1])
                if request_body := val.get("requestBody"):
                    component_ref = self.get_component_obj_name(request_body)
                    if component_ref:
                        self.schema_imports.add(component_ref.split("/")[-1])

    def generate_request_functions(self):
        for url, val in self.paths.items():
            function_info = get_function_info_dict()
            function_info["url"] = url
            for key, val_obj in val.items():
                function_info["method"] = key
                function_info["function_name"] = f"{val_obj['tags'][0]}_" \
                                                 f"{key}_" \
                                                 f"{operation_id_to_function_name(val_obj['operationId'])}"
                if req_body := val_obj.get("requestBody"):
                    if json_data := req_body["content"].get("application/json"):
                        if "items" in json_data["schema"]:
                            obj_name = json_data["schema"]["items"]["$ref"].split("/")[-1]
                            function_info["request_obj"] = f"list[{obj_name}]"
                        else:
                            function_info["request_obj"] = json_data["schema"]["$ref"].split("/")[-1]

                if parameters := val_obj.get("parameters"):
                    query_params = set()
                    for obj in parameters:
                        if obj["in"] == "path":
                            param_name = operation_id_to_function_name(obj["name"])
                            param_type = obj["schema"]["type"]
                            url = url.replace(obj["name"], param_name)
                            function_info["url"] = url
                            function_info["path_parameters"].add(f"{param_name}: {TYPE_CONVERTION[param_type]}")
                        elif obj["in"] == "query":
                            if obj.get("required"):
                                type_info = TYPE_CONVERTION[obj['schema']['type']]
                            else:
                                type_info = f"Optional({TYPE_CONVERTION[obj['schema']['type']]})"

                            query_params.add(f"{obj['name']}: {type_info}")
                    query_param_schema, param_schema_name = self.create_query_param_typedict(
                        function_info["function_name"], query_params
                    )
                    self.schema_imports.add(param_schema_name)
                    self.query_param_schemas.append(query_param_schema)
                    function_info["query_parameters"] = param_schema_name

                if responses := val_obj.get("responses"):
                    for content in responses.values():
                        if resp_content := content.get("content"):
                            if "items" in resp_content["application/json"]["schema"]:
                                resp_ref = resp_content["application/json"]["schema"]["items"]["$ref"]
                            elif "$ref" in resp_content["application/json"]["schema"]:
                                resp_ref = resp_content["application/json"]["schema"]["$ref"]
                            elif "additionalProperties" in resp_content["application/json"]["schema"]:
                                resp_ref = TYPE_CONVERTION[
                                    resp_content["application/json"]["schema"]["additionalProperties"]["type"]
                                ]
                            else:
                                resp_ref = TYPE_CONVERTION[
                                    resp_content["application/json"]["schema"]["type"]
                                ]

                            function_info["response_obj"] = resp_ref.split("/")[-1]
                self.data.append(self.create_request_function_str(function_info))

    def create_request_function_str(self, data: dict) -> str:
        path_parameters = ", ".join(data["path_parameters"])

        function_head_list = []
        request_call_params = []

        if data["request_obj"]:
            function_head_list.extend([f'req_data: {data["request_obj"]}', "/"])
            request_call_params.append("json=req_data.dict()")
        if path_parameters:
            function_head_list.append(path_parameters)
        function_head_list.append("*")
        if query_param := data["query_parameters"]:
            function_head_list.append(f"params: {query_param}")
        function_head_list.extend(["headers: Optional[dict] = None", "proxies: Optional[dict] = None", "**kwargs"])
        request_call_params.extend(["headers=headers_, proxies=proxies_, **kwargs"])

        if data["query_parameters"] and not data["path_parameters"]:
            function_str = Template("""def $function_name($function_params)$response_type:
    
    headers_ = headers if headers is not None else {}
    proxies_ = proxies if proxies is not None else {}
    
    response_obj = requests.$method(url="$url", params=params.dict(), $call_params)
    
    if response_obj.ok:
        return $return_response
    return None
                """)
        elif data["path_parameters"] and not data["query_parameters"]:
            function_str = Template("""def $function_name($function_params)$response_type:
    url = f"$url"
    headers_ = headers if headers is not None else {}
    proxies_ = proxies if proxies is not None else {}
    
    response_obj = requests.$method(url=url, $call_params)
    
    if response_obj.ok:
        return $return_response
    return None
                """)
        elif data["path_parameters"] and data["query_parameters"]:
            function_str = Template("""def $function_name($function_params)$response_type:
    url = f"$url"
    
    headers_ = headers if headers is not None else {}
    proxies_ = proxies if proxies is not None else {}
    
    response_obj = requests.$method(url=url, params=params.dict(), $call_params)
    
    if response_obj.ok:
        return $return_response
    return None
                """)
        else:
            function_str = Template("""def $function_name($function_params)$response_type:
    headers_ = headers if headers is not None else {}
    proxies_ = proxies if proxies is not None else {}
    
    response_obj = requests.$method(url="$url", $call_params)
    
    if response_obj.ok:
        return $return_response
    return None
                """)

        if response_obj := data['response_obj']:
            response_type = f"-> Optional[{response_obj}]"
        else:
            response_type = "-> Any"

        if response_obj := data['response_obj']:
            return_response = f"{response_obj}(**response_obj.json())"
        else:
            return_response = f"response_obj.json()"

        return function_str.substitute(url=data["url"],
                                       method=data["method"],
                                       function_name=data["function_name"],
                                       function_params=", ".join(function_head_list),
                                       call_params=", ".join(request_call_params),
                                       resp_obj=data["response_obj"],
                                       return_response=return_response,
                                       response_type=response_type)

    def generate_apis(self, schema_path: str) -> None:
        self.generate_base_imports()
        self.generate_obj_imports()
        self.generate_request_functions()
        objs_str = ", ".join(self.schema_imports)
        data = [f"from {schema_path} import ({objs_str})", ] + self.data
        data.append("\n")
        self.data = data

    def write_api(self, folder_path: Path):
        text = black.format_str("\n".join(self.data), mode=black.Mode())

        with (folder_path / Path("api.py")) as file:
            file.write_text(text)
