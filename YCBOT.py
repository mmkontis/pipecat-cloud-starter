#
# Copyright (c) 2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

import os

import aiohttp
from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.frames.frames import LLMMessagesFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.elevenlabs import ElevenLabsTTSService
from pipecat.services.openai import OpenAILLMService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecatcloud.agent import DailySessionArguments
from pipecat_flows import FlowManager, FlowConfig, FlowArgs, FlowResult

# Check if we're in local development mode
LOCAL_RUN = os.getenv("LOCAL_RUN")
if LOCAL_RUN:
    import asyncio
    import webbrowser

    try:
        from local_runner import configure
    except ImportError:
        logger.error("Could not import local_runner module. Local development mode may not work.")

# Load environment variables
load_dotenv(override=True)

# Define flow configuration
flow_config: FlowConfig = {
    "initial_node": "greeting",
    "nodes": {
        "greeting": {
            "role_messages": [
                {
                    "role": "system",
                    "content": "You are a Y Combinator partner conducting a 10-minute interview with a startup founder. Be direct and to the point. Ask challenging but fair questions."
                }
            ],
            "task_messages": [
                {
                    "role": "system",
                    "content": "Introduce yourself briefly as a YC partner and ask the founder to describe their startup in one sentence."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_pitch",
                        "description": "Collect the founder's one-sentence pitch",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "pitch": {"type": "string"}
                            },
                            "required": ["pitch"]
                        },
                        "transition_to": "problem_question"
                    }
                }
            ]
        },
        "problem_question": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about the specific problem they're solving and why it matters."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_problem",
                        "description": "Collect information about the problem they're solving",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "problem": {"type": "string"}
                            },
                            "required": ["problem"]
                        },
                        "transition_to": "solution_question"
                    }
                }
            ]
        },
        "solution_question": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about their solution and what makes it unique or defensible."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_solution",
                        "description": "Collect information about their solution",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "solution": {"type": "string"}
                            },
                            "required": ["solution"]
                        },
                        "transition_to": "traction_question"
                    }
                }
            ]
        },
        "traction_question": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about their current traction (users, revenue, growth) and how they've validated demand."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_traction",
                        "description": "Collect information about their traction",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "traction": {"type": "string"}
                            },
                            "required": ["traction"]
                        },
                        "transition_to": "team_question"
                    }
                }
            ]
        },
        "team_question": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about the founding team, their backgrounds, and why they're uniquely positioned to solve this problem."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_team",
                        "description": "Collect information about the founding team",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "team": {"type": "string"}
                            },
                            "required": ["team"]
                        },
                        "transition_to": "market_question"
                    }
                }
            ]
        },
        "market_question": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about their target market size and growth strategy."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_market",
                        "description": "Collect information about their market",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "market": {"type": "string"}
                            },
                            "required": ["market"]
                        },
                        "transition_to": "business_model"
                    }
                }
            ]
        },
        "business_model": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about their business model and how they plan to make money."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_business_model",
                        "description": "Collect information about their business model",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "business_model": {"type": "string"}
                            },
                            "required": ["business_model"]
                        },
                        "transition_to": "challenges"
                    }
                }
            ]
        },
        "challenges": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about their biggest challenges or obstacles and how they plan to overcome them."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_challenges",
                        "description": "Collect information about their challenges",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "challenges": {"type": "string"}
                            },
                            "required": ["challenges"]
                        },
                        "transition_to": "fundraising"
                    }
                }
            ]
        },
        "fundraising": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Ask about their fundraising goals and how they plan to use the investment."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "collect_fundraising",
                        "description": "Collect information about their fundraising plans",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "fundraising": {"type": "string"}
                            },
                            "required": ["fundraising"]
                        },
                        "transition_to": "feedback_intro"
                    }
                }
            ]
        },
        "feedback_intro": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Tell the founder you'll now spend the last 3 minutes providing direct feedback. Ask if they're ready to hear it."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "ready_for_feedback",
                        "description": "Check if founder is ready for feedback",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "ready": {"type": "boolean"}
                            },
                            "required": ["ready"]
                        },
                        "transition_to": "strengths_feedback"
                    }
                }
            ]
        },
        "strengths_feedback": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Provide 1-2 specific strengths of their startup idea, team, or approach. Be direct and concrete, avoiding generic praise."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "acknowledge_strengths",
                        "description": "Acknowledge the strengths feedback",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "acknowledged": {"type": "boolean"}
                            },
                            "required": ["acknowledged"]
                        },
                        "transition_to": "concerns_feedback"
                    }
                }
            ]
        },
        "concerns_feedback": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Provide 1-2 specific concerns or areas for improvement. Be straightforward but constructive, focusing on what would make the startup more fundable."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "acknowledge_concerns",
                        "description": "Acknowledge the concerns feedback",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "acknowledged": {"type": "boolean"}
                            },
                            "required": ["acknowledged"]
                        },
                        "transition_to": "yc_decision"
                    }
                }
            ]
        },
        "yc_decision": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Provide a clear yes/no decision on whether YC would fund this startup based on the interview. If yes, explain why. If no, explain the main reason and what would need to change. Be direct and honest."
                }
            ],
            "functions": [
                {
                    "type": "function",
                    "function": {
                        "name": "acknowledge_decision",
                        "description": "Acknowledge the funding decision",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "acknowledged": {"type": "boolean"}
                            },
                            "required": ["acknowledged"]
                        },
                        "transition_to": "end"
                    }
                }
            ]
        },
        "end": {
            "task_messages": [
                {
                    "role": "system",
                    "content": "Thank the founder for their time and suggest one specific action they should take immediately after the interview to improve their chances of success, regardless of the funding decision."
                }
            ],
            "functions": [],
            "post_actions": [{"type": "end_conversation"}]
        }
    }
}

async def main(room_url: str, token: str):
    """Main pipeline setup and execution function.

    Args:
        room_url: The Daily room URL
        token: The Daily room token
    """
    logger.debug("Starting bot in room: {}", room_url)

    transport = DailyTransport(
        room_url,
        token,
        "bot",
        DailyParams(
            audio_out_enabled=True,
            transcription_enabled=True,
            vad_enabled=True,
            vad_analyzer=SileroVADAnalyzer(),
        ),
    )

    tts = ElevenLabsTTSService(
        api_key=os.getenv("ELEVENLABS_API_KEY"),
        voice_id="pNInz6obpgDQGcFmaJgB",  # Adam voice - professional, authoritative male voice
        model_id="eleven_monolingual_v1",
        optimize_streaming_latency=2,  # Reduce latency
        stability=0.7,  # Increase stability for more consistent delivery
        similarity_boost=0.7,  # Balanced voice clarity
        style=0.3,  # More businesslike speaking style
        use_speaker_boost=True  # Enhance voice clarity
    )

    llm = OpenAILLMService(
        api_key=os.getenv("OPENAI_API_KEY"),
        model="gpt-4o",
        temperature=0.7,  # Lower temperature for more focused responses
        max_tokens=1024,  # Shorter responses
        top_p=0.9,
        frequency_penalty=0.3,  # Reduce repetition
        presence_penalty=0.6,  # Encourage more direct questions
    )

    context = OpenAILLMContext()
    context_aggregator = llm.create_context_aggregator(context)

    pipeline = Pipeline(
        [
            transport.input(),
            context_aggregator.user(),
            llm,
            tts,
            transport.output(),
            context_aggregator.assistant(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(
            allow_interruptions=True,
            enable_metrics=True,
            enable_usage_metrics=True,
            report_only_initial_ttfb=True,
        ),
    )

    # Initialize flow manager
    flow_manager = FlowManager(
        task=task,
        llm=llm,
        context_aggregator=context_aggregator,
        tts=tts,
        flow_config=flow_config,
    )

    @transport.event_handler("on_first_participant_joined")
    async def on_first_participant_joined(transport, participant):
        logger.info("First participant joined: {}", participant["id"])
        await transport.capture_participant_transcription(participant["id"])
        await flow_manager.initialize()

    @transport.event_handler("on_participant_left")
    async def on_participant_left(transport, participant, reason):
        logger.info("Participant left: {}", participant)
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
        await main(args.room_url, args.token)
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
            await main(room_url, token)
    except Exception as e:
        logger.exception(f"Error in local development mode: {e}")


# Local development entry point
if LOCAL_RUN and __name__ == "__main__":
    try:
        asyncio.run(local_main())
    except Exception as e:
        logger.exception(f"Failed to run in local mode: {e}")
