

class PromptManager:
    def __init__(self) -> None:
        pass

    def get_execute_tool_prompt(self, tool_name: str, result: str) -> str:
        return f"""
        "The result of {tool_name} is '{str(result)}'. "
        Is this a final and appropriate answer? If yes, return it in the following JSON format:
        ```json
        {{"result": "The final answer you would say directly to the user."}}
        ```
        If not, think again and select another tool to try.
        """
    
    def get_call_llm_prompt(self, tools_description: list) -> str:
        return f"""
            Tools: {tools_description}
            Format:
            ```json
            {{"name": "tool_name", "arguments": {{"arg1": "value1"}}}}
            ```
            Please strictly follow the format above and return a valid JSON object inside a json code block (```json). The "name" must be the tool name, and "arguments" must contain the input parameters."""


prompt_manager = PromptManager()