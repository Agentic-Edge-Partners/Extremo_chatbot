"""LangGraph ReAct agent for Extremo Ambiente AI assistant."""

from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from agent.prompts import SYSTEM_PROMPT
from agent.tools import ALL_TOOLS

llm = ChatOpenAI(model="gpt-4o", temperature=0.3)

graph = create_react_agent(
    model=llm,
    tools=ALL_TOOLS,
    prompt=SYSTEM_PROMPT,
)
