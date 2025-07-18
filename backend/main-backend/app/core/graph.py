from typing import Dict, Any, List, Annotated
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from app.models.chat import Message, ConversationState
from app.services.llm_client import llm_client
from app.utils.logger import get_logger


logger = get_logger("conversation_graph")


def create_conversation_graph():
    """Create a LangGraph workflow for conversation management."""
    
    # Define the state schema
    workflow = StateGraph(ConversationState)
    
    # Add nodes
    workflow.add_node("process_input", process_user_input)
    workflow.add_node("generate_response", generate_llm_response)
    workflow.add_node("format_output", format_conversation_output)
    
    # Define the workflow
    workflow.set_entry_point("process_input")
    workflow.add_edge("process_input", "generate_response")
    workflow.add_edge("generate_response", "format_output")
    workflow.add_edge("format_output", END)
    
    return workflow.compile()


async def process_user_input(state: ConversationState) -> ConversationState:
    """Process user input and prepare for LLM generation."""
    logger.info("Processing user input")
    
    # Convert messages to LangChain format
    lc_messages = []
    for msg in state.messages:
        if msg.role.value == "user":
            lc_messages.append(HumanMessage(content=msg.content))
        elif msg.role.value == "assistant":
            lc_messages.append(AIMessage(content=msg.content))
        elif msg.role.value == "system":
            lc_messages.append(SystemMessage(content=msg.content))
    
    # Add to metadata for LLM processing
    state.metadata["lc_messages"] = lc_messages
    state.metadata["last_user_message"] = state.messages[-1].content if state.messages else ""
    
    return state


async def generate_llm_response(state: ConversationState) -> ConversationState:
    """Generate response using the LLM agent service."""
    logger.info("Generating LLM response")
    
    try:
        # Create chat request for LLM agent
        from app.models.chat import ChatRequest
        request = ChatRequest(
            messages=state.messages,
            stream=False,  # We'll handle streaming separately
            temperature=0.7,
            model="gpt-4"
        )
        
        # Call LLM agent service
        response = await llm_client.generate_text(request)
        
        # Add response to state
        assistant_message = Message(
            role="assistant",
            content=response.get("response", ""),
            timestamp=response.get("timestamp")
        )
        state.messages.append(assistant_message)
        state.metadata["llm_response"] = response
        
        logger.info("LLM response generated successfully")
        
    except Exception as e:
        logger.error(f"Failed to generate LLM response: {str(e)}")
        # Add error message
        error_message = Message(
            role="assistant",
            content="I apologize, but I encountered an error while processing your request. Please try again.",
            timestamp=None
        )
        state.messages.append(error_message)
        state.metadata["error"] = str(e)
    
    return state


async def format_conversation_output(state: ConversationState) -> ConversationState:
    """Format the final conversation output."""
    logger.info("Formatting conversation output")
    
    # Clean up temporary metadata
    if "lc_messages" in state.metadata:
        del state.metadata["lc_messages"]
    
    # Add conversation summary
    state.metadata["conversation_length"] = len(state.messages)
    state.metadata["last_updated"] = state.messages[-1].timestamp if state.messages else None
    
    return state


# Global graph instance
conversation_graph = create_conversation_graph() 