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
from pipecat.transports.base_transport import TransportParams
from deepgram import LiveOptions
import aiohttp
from dotenv import load_dotenv
from loguru import logger
from PIL import Image
from pipecat.adapters.schemas.function_schema import FunctionSchema
from pipecat.adapters.schemas.tools_schema import ToolsSchema
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    OutputImageRawFrame,
    SpriteFrame,
    TTSSpeakFrame,
    LLMMessagesFrame,
    TranscriptionFrame,
    TextFrame,
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor
from pipecat.processors.frameworks.rtvi import RTVIConfig, RTVIObserver, RTVIProcessor
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.services.google.llm import GoogleLLMService, GoogleLLMContext
from pipecat.services.openai.stt import OpenAISTTService
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments
from pipecat.services.simli.video import SimliVideoService, SimliConfig
from pipecat_flows import FlowManager, FlowConfig
from deepgram import LiveOptions
import asyncio
import json
import google.ai.generativelanguage as glm
from datetime import datetime, timezone

load_dotenv(override=True)

# # --- FlowManager Integration (Temporarily Disabled) ---
# # Load flow configuration from JSON file at module level
# try:
#     # Use the original file name as seen in bot1.py
#     with open("flow_config_therapy.json", "r") as f:
#         flow_config: FlowConfig = json.load(f)
#     # Basic validation
#     if not isinstance(flow_config, dict) or "initial_node" not in flow_config:
#         logger.error("Loaded flow_config_therapy.json is not a valid flow dictionary with 'initial_node'. Bot may not function correctly.")
#         # Set to a minimal valid structure or raise error if preferred
#         flow_config = {"initial_node": None, "nodes": {}}
#     else:
#         logger.info("Successfully loaded flow configuration from flow_config_therapy.json")
# except FileNotFoundError:
#     logger.error("flow_config_therapy.json not found. Please ensure the file exists. Bot cannot run in flow mode.")
#     # Provide a default empty config or raise an error to prevent running without a flow
#     flow_config: FlowConfig = {"initial_node": None, "nodes": {}}
# except json.JSONDecodeError as e:
#     logger.error(f"Error decoding flow_config_therapy.json: {e}. Bot cannot run in flow mode.")
#     # Provide a default empty config or raise an error
#     flow_config: FlowConfig = {"initial_node": None, "nodes": {}}
# # --- End FlowManager Integration (Temporarily Disabled) ---


# Check if we're in local development mode
LOCAL_RUN = os.getenv("LOCAL_RUN")
if LOCAL_RUN:
    import webbrowser

    try:
        from local_runner import configure
    except ImportError:
        logger.error("Could not import local_runner module. Local development mode may not work.")


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
    - Configurable options via the config dictionary
    """
    logger.info(f"Received configuration: {config}")

    # Retrieve configuration values or use defaults/environment variables
    simli_api_key = os.getenv("SIMLI_API_KEY")
    simli_face_id = config.get("simli_face_id", os.getenv("SIMLI_FACE_ID"))
    elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
    elevenlabs_voice_id = config.get("elevenlabs_voice_id", os.getenv("ELEVENLABS_MINAS_VOICE_ID", "Kp00queB4GuYyvQ1gVZn")) # Default fallback if env var missing too
    deepgram_api_key = os.getenv("DEEPGRAM_API_KEY")
    llm_provider = config.get("llm_provider", os.getenv("LLM_PROVIDER", "google")).lower()
    openai_api_key = os.getenv("OPENAI_API_KEY")
    google_api_key = os.getenv("GOOGLE_API_KEY", "AIzaSyCNdv-mYxjvOiSgZta_nGiijQ5IdHDy8iw") # Default fallback

    # Retrieve language setting, default to Greek ('el')
    language = config.get("language", "el")
    logger.info(f"Using language code: {language}")

    # Log the retrieved simli_face_id for debugging
    logger.debug(f"Retrieved simli_face_id (from config or env var): '{simli_face_id}'")

    # Retrieve unused config values and log them
    heygen_video_id = config.get("heygen_video_id")
    cartesia_voice_id = config.get("cartesia_voice_id")

    # Bot will always run in Flow Mode using the globally loaded flow_config
    # logger.info("Bot configured to run in Flow Mode using flow_config_therapy.json.") # Temporarily disabled
    logger.info("Bot running WITHOUT FlowManager, using hardcoded system prompt.")


    # --- Service Initializations ---
    simli = None # Initialize simli to None
    heygen_service = None # Initialize heygen_service to None

    # Check required API keys (excluding Simli/Heygen for now)
    if not elevenlabs_api_key:
        logger.error("ELEVENLABS_API_KEY environment variable not set.")
        raise ValueError("ElevenLabs API Key not configured.")
    if not deepgram_api_key:
        logger.error("DEEPGRAM_API_KEY environment variable not set.")
        raise ValueError("Deepgram API Key not configured.")

    # Conditionally initialize Simli Video Service
    if simli_face_id:
        if not simli_api_key:
            logger.error("SIMLI_API_KEY environment variable not set, but simli_face_id was provided.")
            raise ValueError("Simli API Key not configured for provided Face ID.")
        logger.info(f"Initializing Simli with Face ID: {simli_face_id}")
        simli = SimliVideoService(
            SimliConfig(
                apiKey=simli_api_key,
                faceId=simli_face_id,
                maxIdleTime="1300"
            ))
    else:
        logger.info("No simli_face_id provided. Simli video service will not be used.")

    # Conditionally prepare Heygen Service (Placeholder)
    if heygen_video_id:
        logger.info(f"Received heygen_video_id: {heygen_video_id}. Heygen service would be initialized here.")
        # !!! IMPORTANT: Heygen service integration is not implemented yet. !!!
        # Replace the line below with actual Heygen service initialization when available.
        heygen_service = True # Using True as a placeholder flag
        logger.warning("Heygen video service is enabled but not implemented. No Heygen video will be generated.")
    else:
        logger.info("No heygen_video_id provided. Heygen video service will not be used.")


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
            # Create VADParams object with desired settings
            vad_analyzer=SileroVADAnalyzer(params=VADParams(
                confidence=1, # Renamed from threshold, lower = less sensitive
                stop_secs=0, # Default is 0.8, corresponds to min_silence_duration_ms=800
                start_secs=0, # Default, related to how quickly speech starts
                min_volume=0.6 # Default, another sensitivity measure
            )),
            vad_audio_passthrough=True,  # Pass audio through to Deepgram
        ),
    )

    # Initialize text-to-speech service with speed adjustment
    tts = ElevenLabsTTSService(
        api_key=elevenlabs_api_key,
        voice_id=elevenlabs_voice_id,
        model_id="eleven_flash_v2_5",
        params=ElevenLabsTTSService.InputParams(
            optimize_streaming_latency="1",  # Changed to string
            auto_mode=True,
            speed=0.8,
            use_speaker_boost=True,
            style=0.7 # More natural speaking style
        )
    )

    # Determine LLM provider (default to Google)
    # llm_provider already retrieved from config or env var

    # Initialize LLM service based on provider
    if llm_provider == "openai":
        if not openai_api_key:
            logger.error("OPENAI_API_KEY environment variable not set for OpenAILLMService.")
            raise ValueError("OpenAI API Key not configured.")
        logger.info("Using OpenAI LLM Service")
        llm = OpenAILLMService(
            api_key=openai_api_key,
            model="gpt-4o-mini"  # Or configure model via env var if needed
        )
    else:
        if not google_api_key:
            logger.error("GOOGLE_API_KEY environment variable not set for GoogleLLMService.")
            raise ValueError("Google API Key not configured.")
        logger.info("Using Google LLM Service (default)")
        # Define system instruction here for Google LLM Service
        system_instruction_content = "Εισαι λιγομιλητος και λακωνικος"
        llm = GoogleLLMService(
            api_key=google_api_key,
            model="gemini-1.5-flash-latest", # Or configure model via env var if needed
            system_instruction=system_instruction_content # Pass instruction to the service
        )

    # Determine Deepgram model based on language
    if language == "en":
        deepgram_model = "nova-3-general"
    else:
        deepgram_model = "nova-2-general"

    # Initialize Speech-to-Text service with Deepgram using the configured language and model
    logger.info(f"Initializing Deepgram STT with language: {language}, model: {deepgram_model}")
    stt = DeepgramSTTService(
        api_key=deepgram_api_key,
        live_options=LiveOptions(
            language=language,
            model=deepgram_model,
        )
    )

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

    # Pass your initial messages and tools to the context to initialize the context
    # flow_manager: FlowManager | None = None # Temporarily disabled
    # context: OpenAILLMContext # Original context type
    context: GoogleLLMContext # Use Google-specific context

    # Define initial messages for the context
    initial_messages = [
        glm.Content(role="user", parts=[glm.Part(text="Hello")]),
        glm.Content(role="model", parts=[glm.Part(text="Hi there!")]) # Use 'model' for assistant role in Google context
    ]

    # Initialize empty context; FlowManager will populate it based on the flow.
    # logger.debug("Initializing empty context for Flow Mode.") # Temporarily disabled
    logger.debug("Initializing Google LLM context with initial messages.")
    # context = GoogleLLMContext() # Previous initialization
    # context = GoogleLLMContext(system_instruction=system_instruction_content) # Removed system_instruction from here
    context = GoogleLLMContext(messages=initial_messages)

    context_aggregator = llm.create_context_aggregator(context)

    # ta = TalkingAnimation()

    # RTVI events for Pipecat client UI
    rtvi = RTVIProcessor(config=RTVIConfig(config=[]))

    # Build the pipeline conditionally
    pipeline_processors = [
        transport.input(),
        rtvi,
        stt,
        context_aggregator.user(),
        llm,
        tts,
    ]

    # Conditionally add Heygen placeholder service to the pipeline
    if heygen_service:
        # !!! IMPORTANT: This currently adds nothing functional. Replace with the actual service variable. !!!
        # pipeline_processors.append(heygen_service) # Example: Append the actual service instance
        logger.warning("Heygen service placeholder added to pipeline structure, but it is non-functional.")

    if simli:
        pipeline_processors.append(simli) # Add Simli only if initialized

    pipeline_processors.extend([
        transport.output(),
        context_aggregator.assistant(),
    ])

    # Add your processors to the pipeline
    pipeline = Pipeline(pipeline_processors)

    # Create a PipelineTask to manage the pipeline
    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
        ),
        observers=[RTVIObserver(rtvi)],
    )

    # # --- FlowManager Integration (Temporarily Disabled) ---
    # # Initialize FlowManager if in flow mode (AFTER pipeline and task are created)
    # # Initialize FlowManager (always, as we are always in flow mode now)
    # if task:
    #     logger.debug("Initializing FlowManager.")
    #     # Ensure flow_config is valid before initializing
    #     if flow_config.get("initial_node") is not None:
    #         flow_manager = FlowManager(
    #             task=task,
    #             llm=llm,
    #             context_aggregator=context_aggregator,
    #             tts=tts,
    #             flow_config=flow_config # Use the globally loaded config
    #         )
    #     else:
    #         logger.error("Flow configuration is invalid or missing initial_node. Cannot initialize FlowManager.")
    # else:
    #     logger.error("Task not available for FlowManager initialization.")
    # # --- End FlowManager Integration (Temporarily Disabled) ---


    @rtvi.event_handler("on_client_ready")
    async def on_client_ready(rtvi):
        # Notify the client that the bot is ready
        await rtvi.set_bot_ready()

        # Add placeholder text to UI transcripts
        try:
            logger.debug("Adding placeholder transcripts to RTVI.")
            # Placeholder for user transcript
            user_placeholder = TranscriptionFrame(
                "placeholder_user",
                text="-- Waiting for user --",
                timestamp=datetime.now(timezone.utc)
            )
            await rtvi.process_frame(user_placeholder, FrameDirection.DOWNSTREAM)

            # Placeholder for bot transcript
            bot_placeholder = TextFrame(text="-- Waiting for bot --")
            await rtvi.process_frame(bot_placeholder, FrameDirection.DOWNSTREAM)

            logger.debug("Placeholder transcripts sent to RTVI.")
        except Exception as e:
            logger.error(f"Error sending placeholder transcripts to RTVI: {e}")

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        # Push a static frame to show the bot is listening
        # await task.queue_frame(quiet_frame)
        # Capture the first participant's transcription
        await transport.capture_participant_transcription(participant["id"])

        # --- System Prompt (Hardcoded - Replaces FlowManager Initialization) ---
        # System prompt is now handled by the FlowManager via flow_config_therapy.json # Original comment
        # logger.info("Adding hardcoded system prompt to context.") # Removed: System instruction set at context creation
        # system_prompt_content = "Καλωσόρισε ..." # Removed: Defined above
        # system_prompt = {"role": "system", "content": system_prompt_content} # Removed
        # context.add_message(system_prompt) # Removed: System instruction set at context creation
        # Trigger the LLM to generate the initial message based on the system prompt
        # await task.queue_frame(LLMMessagesFrame([system_prompt])) # Removed: Caused TypeError with GoogleLLMService
        # --- End Hardcoded System Prompt ---


        # --- FlowManager Integration (Temporarily Disabled) ---
        # if flow_manager:
        #     logger.info("Initializing conversation via FlowManager.")
        #     await flow_manager.initialize()
        # else:
        #     logger.error("Cannot start conversation: FlowManager not initialized.")
        # --- End FlowManager Integration (Temporarily Disabled) ---


    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.debug(f"Participant left: {participant}")
        # Cancel the PipelineTask to stop processing
        await task.cancel()

    @transport.event_handler("on_app_message")
    async def handle_app_message(transport, message: any, sender: str):
        logger.info("📨 %s says %s", sender, message)

        user_text_content = None

        # Handle specific commands like ping/pong first
        if isinstance(message, dict) and message.get("command") == "ping":
            await transport.send_app_message({"command": "pong"}, sender)
            logger.debug(f"Responded pong to {sender}")

        # Check if it's the specific user text input dictionary structure
        elif isinstance(message, dict) and message.get('type') == 'user-text-input' and 'data' in message and 'text' in message['data']:
            user_text_content = message['data']['text'].strip()
            
            logger.debug(f"Extracted text '{user_text_content}' from user-text-input message.")

        # Check if it's a plain, non-empty string
        elif isinstance(message, str) and message.strip():
            user_text_content = message.strip()
            logger.debug("Processing plain string app message as user input.")

        # If we extracted valid text content, process it
        if user_text_content:
            try:
                # 1: Update LLM Context
                logger.debug(f"Creating Google Content object for LLM: {user_text_content}")
                llm_part = glm.Part(text=user_text_content)
                llm_content = glm.Content(role="user", parts=[llm_part])
                llm_message_frame = LLMMessagesFrame([llm_content])
                await task.queue_frames([llm_message_frame])
                logger.debug(f"Queued LLMMessagesFrame for LLM context.")

                # 2: Update UI Transcript via RTVI
                if rtvi:
                    try:
                        logger.debug(f"Creating TranscriptionFrame for RTVI UI: {user_text_content}")
                        ui_frame = TranscriptionFrame(
                            sender, # user_id (positional)
                            user_text_content # text (positional)
                        )
                        await rtvi.process_frame(ui_frame, FrameDirection.UPSTREAM)
                        logger.debug("Sent TranscriptionFrame directly to rtvi.process_frame for UI.")
                    except Exception as rtvi_e:
                        logger.error(f"Error sending TranscriptionFrame directly to RTVI: {rtvi_e}")
                else:
                    logger.warning("RTVI object not found, cannot update UI transcript for typed message.")

            except NameError:
                logger.error("Could not process app message: 'task' or 'rtvi' object not found in scope.")
            except Exception as e:
                logger.error(f"Error processing app message: {e}")

        # If it wasn't ping/pong or a recognized text format
        elif not (isinstance(message, dict) and message.get("command") == "ping"):
             logger.warning(f"Received unexpected or non-text app message format from {sender}: {message}")

    runner = PipelineRunner()

    # Add a small delay ONLY if Simli is used, to allow its connection to establish
    if simli:
        logger.debug("Waiting briefly for Simli connection...")
        await asyncio.sleep(3) # Wait 3 seconds (adjust if needed)
        logger.debug("Simli delay complete.")

    logger.debug("Starting pipeline run.")

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
