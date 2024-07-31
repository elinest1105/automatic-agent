import os
import logging
from typing import Union, List
from pydantic import BaseModel, Field
import instructor
import openai
from rich.console import Console

from atomic_agents.lib.components.agent_memory import AgentMemory
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator
from atomic_agents.agents.base_agent import BaseAgent, BaseAgentOutputSchema, BaseAgentConfig, BaseIOSchema
from atomic_agents.lib.tools.search.searxng_tool import SearxNGTool, SearxNGToolConfig, SearxNGToolInputSchema

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Define system prompt information
system_prompt_generator = SystemPromptGenerator(
    background=[
        "This assistant is a product finder AI designed to help users find products based on their preferences by asking clarifying questions.",
    ],
    steps=[
        "Greet the user and introduce yourself as a product finder assistant.",
        "Ask the user questions to gather information about the product they are looking for.",
        "Use the chat responses to gather all necessary information from the user.",
        "Once sufficient information is gathered, use the SearxNGTool to search for products.",
        "Summarize the search results and provide recommendations to the user.",
    ],
    output_instructions=[
        "Always think in steps before answering using internal reasoning.",
        "Provide helpful and relevant information to assist the user.",
        "Be friendly and respectful in all interactions.",
        "Ensure that the chat responses are used to ask clarifying questions and gather information, and the search tool is used to find products.",
    ],
)

# Initialize chat memory
memory = AgentMemory()
initial_memory = [
    {
        "role": "assistant",
        "content": "Hello! I'm your product finder assistant. What kind of product are you looking for today?",
    }
]
memory.load(initial_memory)

console = Console()

# Initialize the client
client = instructor.from_openai(openai.OpenAI())

# Initialize the SearxNGTool
searxng_tool = SearxNGTool(SearxNGToolConfig(base_url=os.getenv("SEARXNG_BASE_URL"), max_results=5))


# Define a custom response schema
class OutputSchema(BaseIOSchema):
    internal_reasoning: List[str] = Field(..., description="The internal reasoning behind the response.")
    chosen_schema: Union[BaseAgentOutputSchema, SearxNGToolInputSchema] = Field(
        ...,
        description="The response from the chat agent. Every response must use chosen_schema to indicate the type of response (A chat message, or a search request)",
    )

    class Config:
        title = "OutputSchema"
        description = "The response schema for the chat agent."


# Create a config for the chat agent
agent_config = BaseAgentConfig(
    client=client,
    system_prompt_generator=system_prompt_generator,
    model="gpt-4o-mini",
    memory=memory,
    output_schema=OutputSchema,
)

# Create a chat agent
agent = BaseAgent(config=agent_config)

console.print("Product Finder Agent is ready.")
console.print(f'Agent: {initial_memory[0]["content"]}')

while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        print("Exiting chat...")
        break

    response = agent.run(agent.input_schema(chat_message=user_input))

    logger.info(f"Chosen schema: {response.chosen_schema}")

    if isinstance(response.chosen_schema, SearxNGToolInputSchema):
        search_results = searxng_tool.run(response.chosen_schema)

        agent.memory.add_message(
            "assistant",
            f"INTERNAL THOUGHT: I have found the following products: {search_results.results}\n\n I will now summarize the results for the user.",
        )
        output = agent.run().chosen_schema.chat_message
    else:
        output = response.chosen_schema.chat_message

    console.print(f"Agent: {output}")
