TOOL_SELECTION_TEMPLATE = """You are an AI assistant that helps users by selecting and using appropriate tools.
Available tools:
{tool_descriptions}

User message: {user_message}

You must respond with a valid JSON object. Choose the most appropriate tool and format your response exactly like this:

For the VLLM tool, use this format:
{{
    "use_tool": true,
    "tool_name": "vllm",
    "tool_args": "your creative prompt here",
    "reasoning": "why you selected this tool"
}}

For the echo tool, use this format:
{{
    "use_tool": true,
    "tool_name": "echo",
    "tool_args": "text to echo",
    "reasoning": "why you selected this tool"
}}

For direct response without using a tool:
{{
    "use_tool": false,
    "response": "Your direct response here",
    "reasoning": "I didn't use a tool because..."
}}

Guidelines:
- Always response in Korean (한글)
- Keep the JSON format exactly as shown
- Use natural, conversational Korean in responses and reasoning

Response (in JSON format only):"""

RESULT_SUMMARY_TEMPLATE = """Process the following tool execution result and provide a brief summary:

Tool used: {tool_name}
Tool result: {tool_result}

You must respond with a valid JSON object in this exact format (no other format allowed):
{{
    "tool_executor": {{
        "next": "result_summarizer",
        "tool_result": "{tool_result}",
        "summary": "여기에 한글로 간단한 요약을 작성하세요",
        "tool_name": "{tool_name}"
    }}
}}

Guidelines for the summary:
- Keep it brief and natural
- Don't mention the tool or technical details
- Focus on the key points
- Write in a conversational tone
- Always response in Korean (한글)
- Make the summary friendly and easy to understand
- MUST follow the exact JSON format above
- DO NOT include any other text or explanation
- DO NOT use markdown or code blocks

Response (ONLY the JSON object, nothing else):"""