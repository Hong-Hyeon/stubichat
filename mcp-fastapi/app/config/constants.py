from enum import Enum


class ErrorMessage(Enum):
    GENERATION_ERROR = "I apologize, but I couldn't process that request."
    JSON_DECODE_ERROR = "I apologize, This is not a valid JSON Format."
    LLM_ERROR = "I apologize, This is not a valid LLM response."
    RESPONSE_ERROR = "I apologize, This is not a valid response."