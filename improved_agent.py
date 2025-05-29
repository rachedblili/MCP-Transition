"""
Changes from naive_agent.py:
- Event loop creation and nest_asyncio dependency removed
- Agent interface converted to fully async
- Tool functions made sync where appropriate (date, web search are I/O bound but sync APIs)
- Redundant deps parameter usage eliminated
- Method naming formatting corrected
- Type hints added for better code clarity
- Error handling made more specific
- Main function converted to proper async execution
"""

import os
from dotenv import load_dotenv
from datetime import date
from tavily import TavilyClient
import json
import asyncio
from typing import List, Dict, Any
from pydantic_ai import Agent as PydanticAgent, RunContext
from pydantic_ai.messages import ModelMessage
from prompts import role, goal, instructions, knowledge

# Load environment variables
load_dotenv()

# Initialize Tavily client
tavily_api_key = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=tavily_api_key)


class Agent:
    def __init__(self, model: str = "gpt-4o-mini"):
        """
        Initialize the Pydantic AI agent.

        Args:
            model: The language model to use
        """
        self.name = "Pydantic Agent"

        # Create the agent with a comprehensive system prompt
        self.agent = PydanticAgent(
            f'openai:{model}',
            system_prompt="\n".join([
                role,
                goal,
                instructions,
                "You have access to two primary tools: date and web_search.",
                knowledge
            ]),
            deps_type=str,
            result_type=str
        )

        # Create tools
        self._create_tools()

        # Conversation history
        self.messages: List[ModelMessage] = []

    def _create_tools(self) -> None:
        """
        Create and register tools for the agent.
        """
        @self.agent.tool
        def date_tool(ctx: RunContext[str]) -> str:
            """Get the current date"""
            today = date.today()
            return today.strftime("%B %d, %Y")

        @self.agent.tool
        def web_search(ctx: RunContext[str], query: str) -> str:
            """Search the web for information"""
            try:
                search_response = tavily_client.search(query)
                raw_results = search_response.get('results', [])

                # Format results for better readability
                formatted_results = []
                for result in raw_results:
                    formatted_result = {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0)
                    }
                    formatted_results.append(formatted_result)

                results_json = json.dumps(formatted_results, indent=2)
                print(f"Web Search Results for '{query}':")
                print(results_json)
                return results_json
            except Exception as e:
                return f"Search failed: {str(e)}"

    async def chat(self, message: str) -> str:
        """
        Send a message and get a response.

        Args:
            message: User's input message

        Returns:
            Assistant's response
        """
        try:
            result = await self.agent.run(
                message,
                message_history=self.messages
            )

            # Maintain conversation history
            self.messages.extend(result.new_messages())
            return result.output

        except Exception as e:
            print(f"Error in chat: {e}")
            return "Sorry, I encountered an error processing your request."

    def clear_chat(self) -> bool:
        """
        Reset the conversation context.

        Returns:
            True if reset was successful
        """
        try:
            self.messages = []
            return True
        except Exception as e:
            print(f"Error clearing chat: {e}")
            return False


async def main():
    """
    Example usage demonstrating the agent interface.
    """
    agent = Agent()

    print("Agent initialized. Type 'exit' or 'quit' to end.")
    while True:
        query = input("You: ")
        if query.lower() in ['exit', 'quit']:
            break

        response = await agent.chat(query)
        print(f"Assistant: {response}")


if __name__ == "__main__":
    asyncio.run(main())