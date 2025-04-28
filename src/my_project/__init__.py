import logging
import click
import os
import requests
import json
from dotenv import load_dotenv
from google_a2a.common.types import AgentSkill, AgentCapabilities, AgentCard
from google_a2a.common.server import A2AServer
from my_project.task_manager import MyAgentTaskManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = "llama2"  # Or the model you have in Ollama

def query_ollama(prompt: str):
    url = f"{OLLAMA_BASE_URL}/api/generate"
    data = {
        "prompt": prompt,
        "model": MODEL_NAME,
        "stream": False
    }
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        return response.json()['response']
    except requests.exceptions.RequestException as e:
        print(f"Error querying Ollama: {e}")
        return None

@click.command()
@click.option("--host", default="localhost")
@click.option("--port", default=10002)
def main(host, port):
    skill = AgentSkill(
        id="my-project-ollama-skill",
        name="Ollama Integration Tool",
        description="Queries a local LLM using Ollama",
        tags=["ollama", "llm"],
        inputModes=["text"],
        outputModes=["text"],
    )
    logging.info(skill)

    capabilities = AgentCapabilities(
        streaming=True
    )
    agent_card = AgentCard(
        name="Ollama Agent",
        description="An agent that integrates with a local Ollama LLM",
        url=f"http://{host}:{port}/",
        version="0.1.0",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        capabilities=capabilities,
        skills=[skill]
    )
    logging.info(agent_card)

    task_manager = MyAgentTaskManager(query_ollama_function=query_ollama)
    server = A2AServer(
        agent_card=agent_card,
        task_manager=task_manager,
        host=host,
        port=port,
    )
    server.start()

if __name__ == "__main__":
    main()
