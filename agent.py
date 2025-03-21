from __future__ import annotations

import logging
import aiohttp  # Make sure you have aiohttp installed (`pip install aiohttp`)
from dotenv import load_dotenv
from typing import Annotated

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
import json  # Import JSON for serialization


# Load environment variables
load_dotenv(dotenv_path=".env.local")

logger = logging.getLogger("my-worker")
logger.setLevel(logging.INFO)


class AssistantFnc(llm.FunctionContext):
    """Handles LLM function calls, including weather retrieval and RPC communication."""

    def __init__(self, ctx: JobContext):
        """Store the JobContext so we can use it for RPC communication."""
        super().__init__()
        self.ctx = ctx  # Store the context

    # makes this function available as a tool
    @llm.ai_callable()
    async def get_weather(
        self,
        location: Annotated[
            str, llm.TypeInfo(description="The location to get the weather for")
        ],
    ):
        """Fetches the weather for a given location and sends it to the Swift app."""
        logger.info(f"Fetching weather for {location}")

        url = f"https://wttr.in/{location}?format=%C+%t"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    weather_data = await response.text()
                    weather_response = f"The weather in {location} is {weather_data}."
                    logger.info(f"Weather data retrieved: {weather_response}")

                    # Send the weather update to the Swift app
                    await self.send_weather_to_swift(location, weather_response)

                    return weather_response
                else:
                    error_msg = f"Failed to get weather data, status code: {response.status}"
                    logger.error(error_msg)
                    return error_msg

    async def send_weather_to_swift(self, location: str, weather_data: str):
        """Sends the weather update to the Swift app using LiveKit RPC."""
        if not self.ctx.room.remote_participants:
            logger.warning("No remote participants available to receive weather update.")
            return

        remote_participant = list(self.ctx.room.remote_participants.values())[0]

        try:
            payload = json.dumps({  # Ensure JSON serialization
                "location": location,
                "weather": weather_data
            })

            logger.info(f"Sending RPC with payload: {payload}")

            await self.ctx.room.local_participant.perform_rpc(
                destination_identity=remote_participant.identity,
                method="display_weather",
                payload=payload  # Ensure it's a JSON string
            )

            logger.info(f"Sent weather update to Swift: {weather_data}")

        except Exception as e:
            logger.error(f"Failed to send RPC to Swift: {e}")

    @llm.ai_callable()
    async def change_background(
        self,
        color: Annotated[
            str, llm.TypeInfo(description="The color to change the background to")
            # looks for something in this realm
        ],
    ): 

        """Sends the weather update to the Swift app using LiveKit RPC."""
        if not self.ctx.room.remote_participants:
            logger.warning("No remote participants available to receive weather update.")
            return

        remote_participant = list(self.ctx.room.remote_participants.values())[0]

        try:
            payload = json.dumps({  # Ensure JSON serialization
                "color": color
            })

            logger.info(f"Sending RPC with payload: {payload}")

            await self.ctx.room.local_participant.perform_rpc(
                destination_identity=remote_participant.identity,
                method="change_background",
                payload=payload  # Ensure it's a JSON string
            )

            logger.info(f"Sent color to Swift: {color}")

        except Exception as e:
            logger.error(f"Failed to send RPC to Swift: {e}")


async def entrypoint(ctx: JobContext):
    """Main entrypoint for connecting the agent to the LiveKit room."""
    logger.info(f"Connecting to room: {ctx.room.name}")
    logger.info(f"LiveKit server URL: {ctx.room.isconnected()}")  # Log server URL

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    logger.info(f"Connected to LiveKit! Room: {ctx.room.name}, Participants: {len(ctx.room.remote_participants)}")

    participant = await ctx.wait_for_participant()
    run_multimodal_agent(ctx, participant)

    logger.info("Agent started and listening for commands.")


def run_multimodal_agent(ctx: JobContext, participant: rtc.RemoteParticipant):
    """Initializes the multimodal AI agent with voice and text processing."""
    logger.info("Starting multimodal agent...")

    model = openai.realtime.RealtimeModel(
        instructions=(
            "You are a voice assistant created by Play Lab at Olin College of Engineering."
            "Your task is to help older people rehabilitate through exercise."
            "You will call functions based on what the user says."
        ),
        modalities=["audio", "text"],
    )

    chat_ctx = llm.ChatContext()
    chat_ctx.append(
        text="Greet the user with a friendly greeting and ask how you can help them today.",
        role="assistant",
    )

    # Pass `ctx` to AssistantFnc so it has access to JobContext for RPC calls
    fnc_ctx = AssistantFnc(ctx)

    agent = MultimodalAgent(
        model=model,
        chat_ctx=chat_ctx,
        fnc_ctx=fnc_ctx,
    )

    agent.start(ctx.room, participant)
    agent.generate_reply()  # Agent starts by greeting the user


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )
