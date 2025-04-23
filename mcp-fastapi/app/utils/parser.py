import json
from typing import Union

from langchain_core.agents import AgentAction, AgentFinish
from app.utils.utils import UtilsFunctions
from app.config.constants import ErrorMessage

utils_functions = UtilsFunctions()


class ExaOneOutputParser:
    """ExaOne 출력을 파싱하는 클래스"""
    def parse(self, text: str) -> Union[AgentAction, AgentFinish]:
        json_str = utils_functions.extract_last_json_block(text)
        if json_str:
            try:
                data = json.loads(json_str)
                if "result" in data:
                    return AgentFinish(return_values={"output": data["result"]}, log=text)
                elif "name" in data and "arguments" in data:
                    return AgentAction(tool=data["name"], tool_input=data["arguments"], log=text)
            except json.JSONDecodeError as e:
                print(e)
                raise Exception(ErrorMessage.JSON_DECODE_ERROR.value)
        else:
            raise Exception(ErrorMessage.LLM_ERROR.value)