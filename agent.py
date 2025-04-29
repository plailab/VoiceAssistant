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
import asyncio

# Load environment variables
load_dotenv(dotenv_path=".env.local")

logger = logging.getLogger("my-worker")
logger.setLevel(logging.INFO)

frontendData = {}

class AssistantFnc(llm.FunctionContext):
    """
    Handles LLM function calls, including weather retrieval and RPC communication.
    
    Args: context of what the user is saying and if it is applicable, will call a function

    """

    def __init__(self, ctx: JobContext):
        """Store the JobContext so we can use it for RPC communication."""
        super().__init__()
        self.ctx = ctx  # Store the context
    
    @llm.ai_callable()
    async def change_background(
        self,
        color: Annotated[
            str, llm.TypeInfo(description="The color to change the background to")
            # looks for something in this realm
        ],
    ): 
        """
        Sends the weather update to the Swift app using LiveKit RPC. (https://docs.livekit.io/home/client/data/rpc/)
        
        Args:
        self (the instantiated class)
        color (string): actual word (ex. blue, green, white, etc) taken from llm using its magical powers
        
        Returns:
        happiness (when it works)
        """

        # If there is no one, don't do anything
        if not self.ctx.room.remote_participants: 
            logger.warning("No remote participants available to receive weather update.")
            return

        # There will only be one person at a time
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


    @llm.ai_callable()
    async def select_exercise(
        self,
        exercise: Annotated[
            str, llm.TypeInfo(description="The exercise the user selected out of the available exercises: ['Shoulder Raises', 'Leg Raises', 'Cross Body Reach']")  # looks for something in this realm
        ],
    ):
        """
        Description: When a user says they want to do an exercise, select the exercise they said given these available exercises: ["Shoulder Raises", "Leg Raises", "Cross Body Reach"]
        Args:
        self (the instantiated class)
        exercise (string): the exercise the user asked for out of the available exercises
        """

        # If there is no one, don't do anything
        if not self.ctx.room.remote_participants: 
            logger.warning("No remote participants available to start the game.")
            return
        
        # There will only be one person at a time
        remote_participant = list(self.ctx.room.remote_participants.values())[0]

        try:
            payload = json.dumps({
                "exercise": exercise
            })

            logger.info(f"Sending RPC with payload: {payload}")

            await self.ctx.room.local_participant.perform_rpc(
                destination_identity=remote_participant.identity,
                method="select_exercise",
                payload=payload  # Ensure it's a JSON string
            )
            logger.info(f"Sent exercise to Swift: {exercise}")
        except Exception as e:
            logger.error(f"Failed to send RPC to Swift: {e}")

    @llm.ai_callable()
    async def start_game(
        self,
        Yes: Annotated[
            str, llm.TypeInfo(description="Starting the game or exercising (boolean),")
            # looks for something in this realm
        ],
    ): 
        """        
        Description: When a user says to start game or start exercising (anything similar to that), it should set the yes variable to true
        Args:
        self (the instantiated class)
        Yes (bool): True or False
        
        Returns:
        happiness (when it works)
        """

        # If there is no one, don't do anything
        if not self.ctx.room.remote_participants: 
            logger.warning("No remote participants available to start the game.")
            return

        # There will only be one person at a time
        remote_participant = list(self.ctx.room.remote_participants.values())[0]

        try:
            payload = json.dumps({  # Ensure JSON serialization
                "Yes": Yes
            })

            logger.info(f"Sending RPC with payload: {payload}")

            await self.ctx.room.local_participant.perform_rpc(
                destination_identity=remote_participant.identity,
                method="start_game",
                payload=payload  # Ensure it's a JSON string
            )

            logger.info(f"Sent start game to Swift: {Yes}")

        except Exception as e:
            logger.error(f"Failed to send RPC to Swift: {e}")

    @llm.ai_callable()
    async def change_reps(
        self,
        reps: Annotated[
            str, llm.TypeInfo(description="Changing the number of reps based off of user feedback (int),")
            # looks for something in this realm
        ],
    ): 
        """        
        Description: When a user says they want to change the number of reps, change it to the number they said
        Args:
        self (the instantiated class)
        reps: (the number of reps the user asked for)
        
        Returns:
        happiness (when it works)
        """

        # If there is no one, don't do anything
        if not self.ctx.room.remote_participants: 
            logger.warning("No remote participants available to start the game.")
            return

        # There will only be one person at a time
        remote_participant = list(self.ctx.room.remote_participants.values())[0]

        try:
            payload = json.dumps({  # Ensure JSON serialization
                "reps": reps
            })

            logger.info(f"Sending RPC with payload: {payload}")

            await self.ctx.room.local_participant.perform_rpc(
                destination_identity=remote_participant.identity,
                method="change_reps",
                payload=payload  # Ensure it's a JSON string
            )

            logger.info(f"Sent rep number: {reps}")

        except Exception as e:
            logger.error(f"Failed to send RPC to Swift: {e}")

async def entrypoint(ctx: JobContext):
    """Main entrypoint for connecting the agent to the LiveKit room."""
    logger.info(f"Connecting to room: {ctx.room.name}")
    logger.info(f"LiveKit server URL: {ctx.room.isconnected()}")  # Log server URL

    @ctx.room.on("data_received")
    def on_data_received(data: rtc.DataPacket):
        async def handle_data():
            try:
                # Parse the incoming data
                logger.info(f"Raw data received: {data}")
                
                # Decode the data from bytes to string and load as JSON
                parsed_data = json.loads(data.data)
                logger.info(f"Parsed data: {parsed_data}")
                frontendData.update(parsed_data)
                logger.info(f"Updated frontendData: {frontendData}")
                
            except Exception as e:
                logger.error(f"Failed to handle incoming data: {e}")
        
        asyncio.create_task(handle_data())

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        logger.info(f"Track subscribed: {track.kind} from participant {participant.identity}")

    # Connect to the room (auto-subscribe to all tracks)
    await ctx.connect(auto_subscribe=AutoSubscribe.SUBSCRIBE_ALL)
    logger.info(f"Connected to LiveKit! Room: {ctx.room.name}, Participants: {len(ctx.room.remote_participants)}")

    participant = await ctx.wait_for_participant()
    run_multimodal_agent(ctx, participant)

    logger.info("Agent started and listening for commands.")


def run_multimodal_agent(ctx: JobContext, participant: rtc.RemoteParticipant):
    """Initializes the multimodal AI agent with voice and text processing."""
    logger.info("Starting multimodal agent...")

    model = openai.realtime.RealtimeModel(
        instructions=(
            "You are a voice assistant created by Plai Lab at Olin College of Engineering."
            "Your task is to help older people rehabilitate through exercise."
            "You will call functions based on what the user says."
            "When the person is exercising, based off the exercise, check on them and ask if they are doing okay"
            "If the form of a user is bad, give some feedback based off the exercise" # we need to do each of this individually
            # We need to do a form checker because I don't trust vision and we don't have vision input with realtime agent...

            # STUFF WILL NEED TO BE PROMPTED BETTER IN THE FUTURE
        ),
        modalities=["audio", "text"],
    )

    chat_ctx = llm.ChatContext()
    chat_ctx.append(
        text=(
            "When you are initialized, say the following exactly as written, without adding or changing anything:"
            "Welcome! Let me guide you through the app. "
            "You can talk to me directly through voice to start exercises on this app. Tap 'Play Start Exercising' to begin your workout, use 'Next Exercise' to explore different exercises, "
            "and adjust the slider to set the number of reps per set. The exercises available are: "
            "['Shoulder Raises', 'Leg Raises', 'Cross Body Reach']. Let's get started! "
        ),
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
