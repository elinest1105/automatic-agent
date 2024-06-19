from pydantic import BaseModel, Field
from atomic_agents.agents.base_chat_agent import BaseAgentIO
import instructor
import openai
from atomic_agents.agents.base_chat_agent import BaseChatAgent, BaseChatAgentConfig
from atomic_agents.lib.components.system_prompt_generator import SystemPromptGenerator, SystemPromptInfo
from examples.deep_research_multi_agent.providers import vector_db_chunks_provider
from examples.deep_research_multi_agent.providers import current_date_provider

class RefineAnswerInputSchema(BaseAgentIO):
    question: str = Field(..., description='The question that was asked.')
    answer: str = Field(..., description='The initial answer to the question.')

class RefineAnswerOutputSchema(BaseModel):
    refined_answer: str = Field(..., description='The refined answer to the question.')

# Create the refine answer agent
refine_answer_agent = BaseChatAgent(
    BaseChatAgentConfig(
        client=instructor.from_openai(openai.OpenAI()), 
        model='gpt-3.5-turbo',
        system_prompt_generator=SystemPromptGenerator(
            SystemPromptInfo(
                background=[
                    "You are an intelligent answer refinement expert.",
                    "Your task is to expand and elaborate on an existing answer to a question using additional context from vector DB chunks."
                ],
                steps=[
                    "You will receive a question or instruction, the initial answer, and additional context from vector DB chunks.",
                    "Expand and elaborate on the initial answer using the additional context to provide a more comprehensive and detailed response."
                ],
                output_instructions=[
                    "Ensure the refined answer is clear, concise, and well-structured.",
                    "Ensure the refined answer is directly relevant to the question and incorporates the additional context provided.",
                    "Add new information and details to make the final answer more elaborate and informative.",
                    "Do not make up any new information; only use the information present in the context."
                ]
            )
        ),
        input_schema=RefineAnswerInputSchema,
        output_schema=RefineAnswerOutputSchema
    )
)

# Register the context providers
refine_answer_agent.register_context_provider('date', current_date_provider)
refine_answer_agent.register_context_provider('vector_db_chunks', vector_db_chunks_provider)