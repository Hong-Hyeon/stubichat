from typing import Dict, Any, List, Annotated
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.models.chat import Message, ConversationState, ChatRequest
from app.utils.logger import get_logger
from datetime import datetime


logger = get_logger("conversation_graph")


def serialize_message(message: Message) -> Dict[str, Any]:
    """Serialize a Message object to ensure JSON compatibility."""
    return {
        "role": message.role.value,
        "content": message.content,
        "timestamp": message.timestamp.isoformat() if message.timestamp else None
    }


def serialize_messages(messages: List[Message]) -> List[Dict[str, Any]]:
    """Serialize a list of Message objects."""
    return [serialize_message(msg) for msg in messages]


def serialize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Serialize metadata to ensure JSON compatibility."""
    serialized = {}
    for key, value in metadata.items():
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def create_conversation_graph():
    """Create a LangGraph workflow for conversation management."""
    
    # Define the state schema
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("validate_input", validate_user_input)
    workflow.add_node("prepare_llm_request", prepare_llm_request)
    workflow.add_node("call_llm_agent", call_llm_agent)
    workflow.add_node("process_llm_response", process_llm_response)
    workflow.add_node("format_output", format_conversation_output)
    
    # Define the workflow
    workflow.set_entry_point("validate_input")
    workflow.add_edge("validate_input", "prepare_llm_request")
    workflow.add_edge("prepare_llm_request", "call_llm_agent")
    workflow.add_edge("call_llm_agent", "process_llm_response")
    workflow.add_edge("process_llm_response", "format_output")
    workflow.add_edge("format_output", END)
    
    return workflow.compile()


async def validate_user_input(state: ConversationState) -> Dict[str, Any]:
    """Validate user input and ensure proper message format."""
    logger.info("Validating user input")
    
    # Ensure we have messages
    if not state.messages:
        raise ValueError("No messages provided in conversation state")
    
    # Validate the last message is from user
    last_message = state.messages[-1]
    if last_message.role.value != "user":
        raise ValueError("Last message must be from user")
    
    # Add validation metadata
    state.metadata["input_validated"] = True
    state.metadata["user_message_count"] = len([m for m in state.messages if m.role.value == "user"])
    state.metadata["assistant_message_count"] = len([m for m in state.messages if m.role.value == "assistant"])
    
    logger.info(f"Input validated. User messages: {state.metadata['user_message_count']}, Assistant messages: {state.metadata['assistant_message_count']}")
    
    return {
        "messages": serialize_messages(state.messages),
        "metadata": serialize_metadata(state.metadata),
        "session_id": state.session_id
    }


async def prepare_llm_request(state: ConversationState) -> Dict[str, Any]:
    """Prepare the request for the LLM agent service."""
    logger.info("Preparing LLM request")
    
    # Create chat request for LLM agent
    # Use the last few messages for context (limit to prevent token overflow)
    context_messages = state.messages[-10:]  # Last 10 messages for context
    
    llm_request = ChatRequest(
        messages=context_messages,
        stream=False,  # We'll handle streaming separately
        temperature=0.7,
        max_tokens=1000,
        model="gpt-4"
    )
    
    # Store the request in metadata (serialize to avoid datetime issues)
    request_dict = llm_request.model_dump()
    # Convert any datetime objects to ISO strings
    for msg in request_dict.get("messages", []):
        if "timestamp" in msg and msg["timestamp"]:
            if hasattr(msg["timestamp"], "isoformat"):
                msg["timestamp"] = msg["timestamp"].isoformat()
    state.metadata["llm_request"] = request_dict
    state.metadata["request_prepared"] = True
    
    logger.info(f"LLM request prepared with {len(context_messages)} context messages")
    
    return {
        "messages": serialize_messages(state.messages),
        "metadata": serialize_metadata(state.metadata),
        "session_id": state.session_id
    }


async def call_llm_agent(state: ConversationState) -> Dict[str, Any]:
    """Call the LLM agent service to generate a response."""
    logger.info("Calling LLM agent service")
    
    try:
        # Get the prepared request
        llm_request_data = state.metadata.get("llm_request")
        if not llm_request_data:
            raise ValueError("LLM request not prepared")
        
        # Convert timestamp strings back to datetime objects for ChatRequest
        for msg in llm_request_data.get("messages", []):
            if "timestamp" in msg and msg["timestamp"] and isinstance(msg["timestamp"], str):
                try:
                    from datetime import datetime
                    msg["timestamp"] = datetime.fromisoformat(msg["timestamp"])
                except ValueError:
                    msg["timestamp"] = None
        
        llm_request = ChatRequest(**llm_request_data)
        
        # Import LLM client here to avoid circular imports
        from app.services.llm_client import LLMClient
        llm_client = LLMClient()
        
        # Call LLM agent service
        response = await llm_client.generate_text(llm_request)
        
        # Store the response in metadata
        state.metadata["llm_response"] = response
        state.metadata["llm_call_successful"] = True
        
        logger.info("LLM agent service called successfully")
        
    except Exception as e:
        logger.error(f"Failed to call LLM agent service: {str(e)}")
        state.metadata["llm_call_successful"] = False
        state.metadata["llm_error"] = str(e)
        raise
    
    return {
        "messages": serialize_messages(state.messages),
        "metadata": serialize_metadata(state.metadata),
        "session_id": state.session_id
    }


async def process_llm_response(state: ConversationState) -> Dict[str, Any]:
    """Process the LLM response and add it to the conversation."""
    logger.info("Processing LLM response")
    
    # Check if LLM call was successful
    if not state.metadata.get("llm_call_successful", False):
        # Add error message
        error_message = Message(
            role="assistant",
            content="I apologize, but I encountered an error while processing your request. Please try again.",
            timestamp=None
        )
        state.messages.append(error_message)
        state.metadata["error_occurred"] = True
        return {
            "messages": serialize_messages(state.messages),
            "metadata": serialize_metadata(state.metadata),
            "session_id": state.session_id
        }
    
    # Get the LLM response
    llm_response = state.metadata.get("llm_response", {})
    
    # Extract response content
    response_content = llm_response.get("response", "")
    if not response_content:
        response_content = "I apologize, but I couldn't generate a response. Please try again."
    
    # Create assistant message
    assistant_message = Message(
        role="assistant",
        content=response_content,
        timestamp=None  # Will be set by default_factory
    )
    
    # Add to conversation
    state.messages.append(assistant_message)
    
    # Update metadata
    state.metadata["response_processed"] = True
    state.metadata["response_length"] = len(response_content)
    state.metadata["model_used"] = llm_response.get("model", "unknown")
    
    logger.info(f"LLM response processed. Response length: {len(response_content)} characters")
    
    return {
        "messages": serialize_messages(state.messages),
        "metadata": serialize_metadata(state.metadata),
        "session_id": state.session_id
    }


async def format_conversation_output(state: ConversationState) -> Dict[str, Any]:
    """Format the final conversation output and clean up metadata."""
    logger.info("Formatting conversation output")
    
    # Clean up temporary metadata
    cleanup_keys = [
        "llm_request", "llm_response", "input_validated", 
        "request_prepared", "llm_call_successful", "response_processed"
    ]
    
    for key in cleanup_keys:
        if key in state.metadata:
            del state.metadata[key]
    
    # Add final conversation metadata
    state.metadata["conversation_length"] = len(state.messages)
    if state.messages:
        last_timestamp = state.messages[-1].timestamp
        state.metadata["last_updated"] = last_timestamp.isoformat() if last_timestamp else None
    else:
        state.metadata["last_updated"] = None
    state.metadata["workflow_completed"] = True
    
    logger.info(f"Conversation output formatted. Total messages: {len(state.messages)}")
    
    return {
        "messages": serialize_messages(state.messages),
        "metadata": serialize_metadata(state.metadata),
        "session_id": state.session_id
    }


# Global graph instance
conversation_graph = create_conversation_graph() 