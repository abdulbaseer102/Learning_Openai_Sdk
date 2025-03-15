import os
from dotenv import load_dotenv
from typing import cast
import chainlit as cl
from agents import Agent, InputGuardrail, GuardrailFunctionOutput, Runner, AsyncOpenAI, OpenAIChatCompletionsModel
from agents.run import RunConfig
from pydantic import BaseModel

# Load API key from .env
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")

# Raise error if API key is missing
if not gemini_api_key:
    raise ValueError("GEMINI_API_KEY is not set. Please ensure it is defined in your .env file.")

# Initialize AI Model
external_client = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

model = OpenAIChatCompletionsModel(
    model="gemini-2.0-flash",
    openai_client=external_client
)

config = RunConfig(
    model=model,
    model_provider=external_client,
    tracing_disabled=True
)

# Define Output Model for Homework Check


# Define AI Agents
math_tutor_agent = Agent(
    name="Math Tutor",
    instructions="You provide help with math problems. Explain your reasoning at each step and include examples.",
    model=model
)

history_tutor_agent = Agent(
    name="History Tutor",
    handoff_description="Specialist agent for historical questions",
    instructions="You provide assistance with historical queries. Explain important events and context clearly.",
    model=model
)

openai_sdk_agent = Agent(
    name="OpenAI SDK Expert",
    handoff_description="You are a specialist agent for teaching OpenAI SDK framework for agent development.",
    instructions="You provide assistance with OpenAI SDK framework queries. Explain concepts clearly with examples.",
    model=model
)



# Guardrail Function to Check for Homework



# Triage Agent to Route Queries
triage_agent = Agent(
    name="Triage Agent",
    instructions="You determine which agent to use based on the user's query.",
    handoffs=[history_tutor_agent, math_tutor_agent, openai_sdk_agent],
    model=model
)

# Chainlit Session Start
@cl.on_chat_start
async def start():
    """Initialize the chat session when a user connects."""
    cl.user_session.set("chat_history", [])
    cl.user_session.set("config", config)
    cl.user_session.set("agent", triage_agent)

    await cl.Message(content="Welcome! How can I assist you today?").send()

# Chainlit Message Handler
@cl.on_message
async def main(message: cl.Message):
    """Process incoming user messages and generate responses."""
    msg = cl.Message(content="Thinking...")
    await msg.send()

    agent: Agent = cast(Agent, cl.user_session.get("agent"))
    config: RunConfig = cast(RunConfig, cl.user_session.get("config"))

    history = cl.user_session.get("chat_history") or []
    history.append({"role": "user", "content": message.content})

    try:
        print("\n[CALLING_AGENT_WITH_CONTEXT]\n", history, "\n")
        result = Runner.run_sync(agent, history, run_config=config)

        response_content = result.final_output
        msg.content = response_content
        await msg.update()

        history.append({"role": "assistant", "content": response_content})
        cl.user_session.set("chat_history", history)

        print(f"User: {message.content}")
        print(f"Assistant: {response_content}")

    except Exception as e:
        msg.content = f"Error: {str(e)}"
        await msg.update()
        print(f"Error: {str(e)}")
