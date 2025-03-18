from __future__ import annotations

import logging
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    llm,
)
from livekit.agents.multimodal import MultimodalAgent
from livekit.plugins import openai

import aiohttp # do I need to download something??
from typing import Annotated


# first define a class that inherits from llm.FunctionContext
class AssistantFnc(llm.FunctionContext):
    # the llm.ai_callable decorator marks this function as a tool available to the LLM
    # by default, it'll use the docstring as the function's description
    @llm.ai_callable()
    async def get_weather(
        self,
        # by using the Annotated type, arg description and type are available to the LLM
        location: Annotated[
            str, llm.TypeInfo(description="The location to get the weather for")
        ],
    ):
        """Called when the user asks about the weather. This function will return the weather for the given location."""
        logger.info(f"getting weather for {location}")
        url = f"https://wttr.in/{location}?format=%C+%t"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    weather_data = await response.text()
                    # response from the function call is returned to the LLM
                    # as a tool response. The LLM's response will include this data
                    return f"The weather in {location} is {weather_data}."
                else:
                    raise f"Failed to get weather data, status code: {response.status}"

fnc_ctx = AssistantFnc()


load_dotenv(dotenv_path=".env.local")
logger = logging.getLogger("my-worker")
logger.setLevel(logging.INFO)


async def entrypoint(ctx: JobContext):
    logger.info(f"connecting to room {ctx.room.name}")
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    participant = await ctx.wait_for_participant()

    run_multimodal_agent(ctx, participant)

    logger.info("agent started")


def run_multimodal_agent(ctx: JobContext, participant: rtc.RemoteParticipant):
    logger.info("starting multimodal agent")

    model = openai.realtime.RealtimeModel(
        instructions=(      
            "You are a voice assistant created by Play Lab at Olin College of Engineering."
            "Your task is to help older people rehabiliate for exercise"
            "You will call functions based off of what the user says"
        ),
        modalities=["audio", "text"],
    )

    # create a chat context with chat history, these will be synchronized with the server
    # upon session establishment
    chat_ctx = llm.ChatContext()
    chat_ctx.append(
        text=
        "Greet the user with a friendly greeting and ask how you can help them today.",
        role="assistant",
    )

    agent = MultimodalAgent(
        model=model,
        chat_ctx=chat_ctx,
        fnc_ctx=fnc_ctx
    )
    agent.start(ctx.room, participant)

    # to enable the agent to speak first
    agent.generate_reply()


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
