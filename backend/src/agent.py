import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    inference,
    room_io,
    tokenize,
)
from livekit.plugins import (
    google,
    murf,
    noise_cancellation,
    silero,
)
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from src.memory import (
    get_user_memory,
    init_database,
    save_user_memory as db_save_user_memory,
)

logger = logging.getLogger("bharatmoney")

load_dotenv(".env.local")


SYSTEM_PROMPT = """
IDENTITY:

You are BharatMoney Voice AI, a friendly financial education voice assistant
for the Financial Services track of VoiceForBharat.

You help people in India understand savings, budgeting, banking, UPI, loans,
EMI, interest, and digital payment safety.

You are an educational assistant. You are not a bank, government authority,
licensed financial advisor, loan provider, or payment service.


MEMORY RULES:

You have two tools:

1. lookup_user
2. save_user_memory

Never save personal information without explicit permission.


NEW CALLER:

When the caller tells you their name, ask permission before saving it.

Example:

Caller:
"Mera naam Danish hai."

Assistant:
"Namaste Danish! Aapse milkar khushi hui. Kya aap chahte hain ki main aapka
naam next time ke liye yaad rakhoon?"

Wait for the caller's answer.

If the caller clearly says YES, call save_user_memory.

If the caller says NO, do not save.

Never treat silence as permission.


RETURNING CALLER:

If saved memory exists, greet the caller naturally by name.

Example:

"Namaste Danish, welcome back! Last time hum savings ke baare mein baat kar
rahe the. Kya aap usi topic ko continue karna chahenge?"


SAFE MEMORY:

You may save:

- Name
- Preferred language
- Financial education topic
- Schemes already discussed
- General eligibility answers voluntarily provided

NEVER SAVE:

- OTP
- UPI PIN
- PIN
- CVV
- Password
- Full bank account number
- Full card number
- Authentication credentials


FINANCIAL SAFETY:

Never ask for OTP.

Never ask for UPI PIN.

Never ask for PIN.

Never ask for CVV.

Never ask for password.

Never ask for a full bank account number.

Never ask for a full card number.

Never claim to access a bank account.

Never claim to check balances or transactions.

Never perform banking transactions.

Never guarantee loans, schemes, investments, insurance, or financial outcomes.


LANGUAGE:

Mirror the caller.

English = simple English.
Hindi = natural Hindi.
Hinglish = natural Hinglish.

Never criticize grammar or pronunciation.


VOICE STYLE:

Keep answers short and conversational.

Prefer two or three short sentences.

Ask one question at a time.


FIRST GREETING:

"Namaste! Main BharatMoney Voice AI hoon. I can help you understand savings,
budgeting, UPI, loans, EMI, and digital payment safety. Aap mujhse Hindi,
English, ya Hinglish mein baat kar sakte hain. Aaj main aapki kaise help
kar sakti hoon?"

Do not call memory tools during the first greeting.
"""


class Assistant(Agent):

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id

        super().__init__(
            instructions=SYSTEM_PROMPT,
        )

    @function_tool
    async def lookup_user(
        self,
        context: RunContext,
    ) -> str:
        """Look up saved memory for the current caller."""

        try:
            memory = get_user_memory(self.user_id)

            if not memory:
                logger.info(
                    "No saved memory",
                    extra={"user_id": self.user_id},
                )
                return "No saved memory exists for this caller."

            logger.info(
                "Saved memory found",
                extra={"user_id": self.user_id},
            )

            return (
                f"Saved memory found. "
                f"Name: {memory.get('name', '')}. "
                f"Language: {memory.get('language_preference', '')}. "
                f"Facts: {memory.get('facts', {})}."
            )

        except Exception:
            logger.exception("Memory lookup failed")
            return "No saved memory is currently available."

    @function_tool
    async def save_user_memory(
        self,
        context: RunContext,
        name: str,
        language_preference: str,
        financial_topic: str,
        permission_granted: bool,
    ) -> str:
        """Save safe caller memory only after explicit permission."""

        if permission_granted is not True:
            return "Memory was not saved because permission was not granted."

        forbidden_terms = (
            "otp",
            "upi pin",
            "pin",
            "cvv",
            "password",
            "account number",
            "card number",
        )

        combined = (
            f"{name} {language_preference} {financial_topic}"
        ).lower()

        if any(term in combined for term in forbidden_terms):
            return (
                "I cannot save sensitive banking information. "
                "Please never share your OTP, PIN, CVV, password, "
                "or full account or card number."
            )

        try:
            saved = db_save_user_memory(
                user_id=self.user_id,
                name=name,
                language_preference=language_preference,
                facts={
                    "financial_topic": financial_topic,
                },
            )

            logger.info(
                "Memory saved successfully",
                extra={
                    "user_id": self.user_id,
                    "name": name,
                },
            )

            return f"Memory saved successfully for {saved['name']}."

        except Exception:
            logger.exception("Memory save failed")
            return (
                "I could not save the memory right now. "
                "We can continue normally."
            )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

    init_database()

    logger.info("BharatMoney memory database ready")


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):

    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    await ctx.connect()

    # Get persistent caller identity from frontend.
    user_id = "unknown"

    if ctx.room.remote_participants:
        participant = next(
            iter(ctx.room.remote_participants.values())
        )
        user_id = participant.identity

    logger.info(
        "BharatMoney session started",
        extra={
            "room": ctx.room.name,
            "user_id": user_id,
        },
    )

    session = AgentSession(

        # LiveKit Inference + Deepgram Nova-3
        stt=inference.STT(
            model="deepgram/nova-3-general",
            language="multi",
        ),

        # Gemini
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),

        # Murf Falcon TTS
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(
                min_sentence_len=1
            ),
            text_pacing=True,
            min_buffer_size=1,
            max_buffer_delay_in_ms=0,
            streaming=True,
        ),

        # Supported turn detector in your installed version
        turn_detection=MultilingualModel(),

        # Silero VAD
        vad=ctx.proc.userdata["vad"],

        # Faster generation
        preemptive_generation=True,

        # Responsive timing
        min_endpointing_delay=0.3,
        max_endpointing_delay=1.5,

        # IMPORTANT:
        # Prevent microphone feedback from interrupting the agent.
        allow_interruptions=False,
    )

    await session.start(
        agent=Assistant(
            user_id=user_id,
        ),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # First greeting.
    await session.generate_reply(
        instructions=(
            "Start the conversation now. Say the FIRST GREETING from your "
            "instructions. Keep it natural and concise. Do not call "
            "lookup_user or save_user_memory during the first greeting."
        )
    )


if __name__ == "__main__":
    cli.run_app(server)