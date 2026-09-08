from langgraph.graph import StateGraph,START,END
from typing import Annotated
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
import os
load_dotenv()

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class ChatState(BaseModel):
    user_input: Annotated[list[BaseMessage], add_messages]
    bot_response: Annotated[list[BaseMessage], add_messages]


model = ChatGroq(
    model_name="openai/gpt-oss-120b",
    api_key=os.environ.get("GROQ_API_KEY"),
    temperature=0.7,
    streaming=True,
    stop=None,
)

graph = StateGraph(ChatState)


def ChatGroq_llm(state: ChatState):
    conversation = []
    for index, user_message in enumerate(state.user_input):
        conversation.append(f"User: {user_message.content}")
        if index < len(state.bot_response):
            conversation.append(f"Assistant: {state.bot_response[index].content}")

    prompt = "You are a helpful assistant. Use the conversation history to answer the latest question.\n\n"
    prompt += "\n".join(conversation)
    bot_response = model.invoke(input=prompt)
    return {"bot_response": [bot_response]}

checkpoint = InMemorySaver()
graph = StateGraph(ChatState)
graph.add_node("LLm_node", ChatGroq_llm)
graph.add_edge(START, "LLm_node")
graph.add_edge("LLm_node", END)
chatbot = graph.compile(checkpointer=checkpoint)
