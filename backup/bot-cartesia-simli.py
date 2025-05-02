#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""OpenAI Bot Implementation.

This module implements a chatbot using OpenAI's GPT-4 model for natural language
processing. It includes:
- Real-time audio/video interaction through Daily
- Animated robot avatar
- Text-to-speech using ElevenLabs
- Support for both English and Spanish

The bot runs as part of a pipeline that processes audio/video frames and manages
the conversation flow.
"""

import os
from pipecat.pipeline.task import PipelineParams, PipelineTask

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from PIL import Image
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    OutputImageRawFrame,
    SpriteFrame,
    TTSSpeakFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments
from pipecat.services.simli import SimliVideoService, SimliConfig

load_dotenv(override=True)
simli = SimliVideoService(
        SimliConfig(
            apiKey="eyznb7kh6cczfp2u93dhcd",
            faceId="2f982412-ca6d-4dd5-83ee-8abf494e0784",
            # handleSilence=False,
            maxIdleTime="1300"
        ))
# Check if we're in local development mode
LOCAL_RUN = os.getenv("LOCAL_RUN")
if LOCAL_RUN:
    import asyncio
    import webbrowser

    try:
        from local_runner import configure
    except ImportError:
        logger.error("Could not import local_runner module. Local development mode may not work.")

# Logger for local dev
# logger.add(sys.stderr, level="DEBUG")

# sprites = []
# script_dir = os.path.dirname(__file__)

# # Load sequential animation frames
# for i in range(1, 26):
#     # Build the full path to the image file
#     full_path = os.path.join(script_dir, f"assets/robot0{i}.png")
#     # Get the filename without the extension to use as the dictionary key
#     # Open the image and convert it to bytes
#     with Image.open(full_path) as img:
#         sprites.append(OutputImageRawFrame(image=img.tobytes(), size=img.size, format=img.format))

# # Create a smooth animation by adding reversed frames
# flipped = sprites[::-1]
# sprites.extend(flipped)

# # Define static and animated states
# quiet_frame = sprites[0]  # Static frame for when bot is listening
# talking_frame = SpriteFrame(images=sprites)  # Animation sequence for when bot is talking


# class TalkingAnimation(FrameProcessor):
#     """Manages the bot's visual animation states.

#     Switches between static (listening) and animated (talking) states based on
#     the bot's current speaking status.
#     """

#     def __init__(self):
#         super().__init__()
#         self._is_talking = False

#     async def process_frame(self, frame: Frame, direction: FrameDirection):
#         """Process incoming frames and update animation state.

#         Args:
#             frame: The incoming frame to process
#             direction: The direction of frame flow in the pipeline
#         """
#         await super().process_frame(frame, direction)

#         # Switch to talking animation when bot starts speaking
#         if isinstance(frame, BotStartedSpeakingFrame):
#             if not self._is_talking:
#                 await self.push_frame(talking_frame)
#                 self._is_talking = True
#         # Return to static frame when bot stops speaking
#         elif isinstance(frame, BotStoppedSpeakingFrame):
#             await self.push_frame(quiet_frame)
#             self._is_talking = False

#         await self.push_frame(frame, direction)


async def fetch_weather_from_api(function_name, tool_call_id, args, llm, context, result_callback):
    """Fetch weather data dummy function.

    This function simulates fetching weather data from an external API.
    It demonstrates how to call an external service from the language model.
    """
    await llm.push_frame(TTSSpeakFrame("Let me check on that."))
    await result_callback({"conditions": "nice", "temperature": "75"})


async def main(room_url: str, token: str, config: dict):
    """Main bot execution function.

    Sets up and runs the bot pipeline including:
    - Daily video transport
    - Speech-to-text and text-to-speech services
    - Language model integration
    - Animation processing
    - RTVI event handling
    """
    logger.info(f"Body: {config}")

    # Set up Daily transport with video/audio parameters
    transport = DailyTransport(
        room_url,
        token,
        "Simple Chatbot",
        DailyParams(
            audio_out_enabled=True,  # Enable output audio for the bot
            camera_out_enabled=True,  # Enable the camera output for the bot
            camera_out_width=512,  # Set the camera output width
            camera_out_height=512,  # Set the camera output height
            transcription_enabled=False,  # Disable Daily's transcription as we're using Deepgram
            vad_enabled=True,  # Enable VAD to handle user speech
            vad_analyzer=SileroVADAnalyzer(),  # Use the Silero VAD analyzer
            vad_audio_passthrough=True,  # Pass audio through VAD for user speech to the rest of the pipeline
        ),
    )

    # Initialize text-to-speech service
    tts = CartesiaTTSService(
        api_key=os.getenv("CARTESIA_API_KEY"),
        voice_id="f61ca2f7-a29a-4e7e-832c-5fe123331ef6",  # Movieman
    )

    # Initialize Speech-to-Text service with Deepgram
    stt = DeepgramSTTService(
        api_key=os.getenv("DEEPGRAM_API_KEY"),
        language="en-US",
        model="nova-3",
        smart_format=True,
        punctuate=True,
        interim_results=True
    )

    # Initialize LLM service
    llm = OpenAILLMService(api_key=os.getenv("OPENAI_API_KEY"), model="gpt-4o")

    # Register your function call providing the function name and callback
    llm.register_function("get_current_weather", fetch_weather_from_api)

    # Define your function call using the FunctionSchema
    # Learn more about function calling in Pipecat:
    # https://docs.pipecat.ai/guides/features/function-calling
    weather_function = FunctionSchema(
        name="get_current_weather",
        description="Get the current weather",
        properties={
            "location": {
                "type": "string",
                "description": "The city and state, e.g. San Francisco, CA",
            },
            "format": {
                "type": "string",
                "enum": ["celsius", "fahrenheit"],
                "description": "The temperature unit to use. Infer this from the user's location.",
            },
        },
        required=["location", "format"],
    )

    # Set up the tools schema with your weather function call
    tools = ToolsSchema(standard_tools=[weather_function])

    # Set up initial messages for the bot
    messages = [
        {
            "role": "system",
            "content": "You are Chatbot, a friendly, helpful robot. Your goal is to demonstrate your capabilities in a succinct way. Your output will be converted to audio so don't include special characters in your answers. Respond to what the user said in a creative and helpful way, but keep your responses brief. Start by introducing yourself.",
        },
    ]

    # Set up conversation context and management
    # The context_aggregator will automatically collect conversation context
    # Pass your initial messages and tools to the context to initialize the context
    context = OpenAILLMContext(messages, tools)
    context_aggregator = llm.create_context_aggregator(context)

    # ta = TalkingAnimation()

    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # Add your processors to the pipeline
    pipeline = Pipeline(
        [
            transport.input(),
            rtvi,
            stt,
            context_aggregator.user(),
            llm,
            tts,
            simli,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    # Create a PipelineTask to manage the pipeline
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        idle_timeout_secs=1300,  # 10 minute timeout
        observers=[RTVIObserver(rtvi)],
    )

    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        # Notify the client that the bot is ready
        await rtvi.set_bot_ready()

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        # Push a static frame to show the bot is listening
        # await task.queue_frame(quiet_frame)
        # Capture the first participant's transcription
        await transport.capture_participant_transcription(participant["id"])
        # Kick off the conversation by pushing a context frame to the pipeline
        await task.queue_frames([context_aggregator.user().get_context_frame()])

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.debug(f"Participant left: {participant}")
        # Cancel the PipelineTask to stop processing
        await task.cancel()

    runner = PipelineRunner()

    await runner.run(task)


async def bot(args: DailySessionArguments):
    """Main bot entry point compatible with the FastAPI route handler.

    Args:
        room_url: The Daily room URL
        token: The Daily room token
        body: The configuration object from the request body
        session_id: The session ID for logging
    """
    logger.info(f"Bot process initialized {args.room_url} {args.token}")

    try:
        await main(args.room_url, args.token, args.body)
        logger.info("Bot process completed")
    except Exception as e:
        logger.exception(f"Error in bot process: {str(e)}")
        raise


# Local development functions
async def local_main():
    """Function for local development testing."""
    try:
        async with aiohttp.ClientSession() as session:
            (room_url, token) = await configure(session)
            logger.warning("_")
            logger.warning("_")
            logger.warning(f"Talk to your voice agent here: {room_url}")
            logger.warning("_")
            logger.warning("_")
            webbrowser.open(room_url)
            await main(room_url, token, config={})
    except Exception as e:
        logger.exception(f"Error in local development mode: {e}")


# Local development entry point
if LOCAL_RUN and __name__ == "__main__":
    try:
        asyncio.run(local_main())
    except Exception as e:
        logger.exception(f"Failed to run in local mode: {e}")
