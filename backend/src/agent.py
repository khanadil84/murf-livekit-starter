import asyncio
import json
import logging
import os
import re
import urllib.request
import uuid
from datetime import datetime, timezone

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

MEMORY TOOLS:

You have two memory tools:

1. lookup_user
2. save_user_memory

Never save personal information without explicit permission.

When the caller tells you their name, ask permission before saving it.

Example:

Caller:
"Mera naam Adil hai."

Assistant:
"Namaste Adil! Aapse milkar khushi hui. Kya aap chahte hain ki main
aapka naam next time ke liye yaad rakhoon?"

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

DAY 5 REAL DATA TOOL:

You also have this tool:

3. check_pmjdy_information

Use check_pmjdy_information whenever the caller asks about:

- PM Jan Dhan Yojana
- PMJDY
- Jan Dhan account
- PMJDY benefits
- PMJDY account features
- PMJDY minimum balance
- where to open a PMJDY account
- current PMJDY information

For current PMJDY information, call the tool instead of relying only on
your own knowledge.

The tool obtains information from the official Government of India
PMJDY website.

If the tool fails, clearly tell the caller that the official information
source could not be reached.

Never invent current scheme information.


DAY 7 HUMAN HELP:

You must ask for human help in these two situations:

1. POSSIBLE FRAUD:
If the caller reports possible fraud, unauthorized transactions,
UPI fraud, card fraud, or suspicious financial activity.

2. FINANCIAL DECISION:
If the caller asks you to make a personal financial decision
that you cannot safely or reliably make, such as deciding whether
they personally qualify for a financial product.

Before creating an escalation:

1. Explain why human help is needed.
2. Tell the caller exactly what short information you want to share:
   - what happened
   - what you already checked
   - urgency
   - caller language
   - preferred follow-up method
3. Ask for explicit permission to share this summary with a human.
4. Do NOT create the escalation if the caller says no.
5. Never include OTP, PIN, UPI PIN, CVV, password, full account number,
   or full card number in the escalation.

Only call create_escalation after the caller clearly gives permission.

After successful creation, give the caller the reference ID and explain
that a human can review the request. Never promise an immediate response.

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
    async def create_escalation(
        self,
        context: RunContext,
        reason: str,
        what_happened: str,
        what_was_checked: str,
        urgency: str,
        caller_language: str,
        preferred_follow_up: str,
        permission_granted: bool,
    ) -> str:
        """
        Create a human-help request only after explicit caller permission.
        """

        if permission_granted is not True:
            logger.info(
                "Escalation not created because permission was not granted",
                extra={"user_id": self.user_id},
            )

            return (
                "I did not create a human-help request because "
                "permission was not granted."
            )

        sensitive_terms = (
            "otp",
            "upi pin",
            "pin",
            "cvv",
            "password",
            "account number",
            "card number",
        )

        combined = (
            f"{reason} "
            f"{what_happened} "
            f"{what_was_checked}"
        ).lower()

        if any(term in combined for term in sensitive_terms):
            logger.warning(
                "Escalation blocked because sensitive information was detected",
                extra={"user_id": self.user_id},
            )

            return (
                "I cannot create the request with sensitive banking "
                "information. Please do not share OTP, PIN, CVV, "
                "password, or full account or card numbers."
            )

        reference_id = "ESC-" + uuid.uuid4().hex[:8].upper()

        escalation = {
            "reference_id": reference_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "user_id": self.user_id,
            "reason": reason,
            "what_happened": what_happened,
            "what_was_checked": what_was_checked,
            "urgency": urgency,
            "caller_language": caller_language,
            "preferred_follow_up": preferred_follow_up,
            "status": "OPEN",
        }

        backend_dir = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        escalation_file = os.path.join(
            backend_dir,
            "escalations.json",
        )

        try:
            existing = []

            if os.path.exists(escalation_file):
                with open(
                    escalation_file,
                    "r",
                    encoding="utf-8",
                ) as file:
                    try:
                        existing = json.load(file)
                    except json.JSONDecodeError:
                        existing = []

            existing.append(escalation)

            with open(
                escalation_file,
                "w",
                encoding="utf-8",
            ) as file:
                json.dump(
                    existing,
                    file,
                    indent=2,
                    ensure_ascii=False,
                )

            logger.info(
                "Human escalation created",
                extra={
                    "reference_id": reference_id,
                    "reason": reason,
                    "urgency": urgency,
                    "user_id": self.user_id,
                },
            )

            return (
                f"Human-help request created successfully. "
                f"Reference ID: {reference_id}. "
                "Tell the caller that the request is open and "
                "a human can review it. Do not promise an immediate response."
            )

        except Exception:
            logger.exception("Failed to create human escalation")

            return (
                "I could not create the human-help request right now. "
                "Please try again later."
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
            return (
                "Memory was not saved because permission was not granted."
            )

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

    @function_tool
    async def check_pmjdy_information(
        self,
        context: RunContext,
    ) -> str:
        """
        Fetch current PM Jan-Dhan Yojana information from the official
        Government of India PMJDY website.

        Use this when the caller asks about PMJDY, Jan Dhan accounts,
        account benefits, minimum balance, account opening, or current
        PMJDY information.
        """

        url = "https://pmjdy.gov.in/scheme"

        def fetch_page() -> str:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 BharatMoney-VoiceAI/1.0"
                    )
                },
            )

            with urllib.request.urlopen(
                request,
                timeout=8,
            ) as response:
                return response.read().decode(
                    "utf-8",
                    errors="ignore",
                )

        try:
            logger.info(
                "Fetching official PMJDY information",
                extra={
                    "user_id": self.user_id,
                    "source": url,
                },
            )

            html = await asyncio.to_thread(fetch_page)

            if not html:
                raise RuntimeError(
                    "Official PMJDY website returned empty data."
                )

            text = re.sub(
                r"<script.*?</script>",
                " ",
                html,
                flags=re.IGNORECASE | re.DOTALL,
            )

            text = re.sub(
                r"<style.*?</style>",
                " ",
                text,
                flags=re.IGNORECASE | re.DOTALL,
            )

            text = re.sub(
                r"<[^>]+>",
                " ",
                text,
            )

            text = re.sub(
                r"\s+",
                " ",
                text,
            ).strip()

            text_lower = text.lower()

            useful_phrases = []

            keywords = (
                "zero balance",
                "minimum balance",
                "bank mitra",
                "bank branch",
                "savings",
                "deposit account",
                "financial services",
                "rupey debit card",
                "overdraft",
            )

            for keyword in keywords:
                position = text_lower.find(keyword)

                if position != -1:
                    start = max(0, position - 180)
                    end = min(
                        len(text),
                        position + 350,
                    )

                    snippet = text[start:end]

                    if snippet not in useful_phrases:
                        useful_phrases.append(snippet)

            if not useful_phrases:
                logger.warning(
                    "PMJDY page loaded but no useful text was extracted"
                )

                return (
                    "I reached the official PMJDY website, but I could "
                    "not extract the required information right now. "
                    "I don't want to guess. Please try again shortly."
                )

            result = " ".join(useful_phrases[:3])

            if len(result) > 1800:
                result = result[:1800] + "..."

            logger.info(
                "Official PMJDY information fetched successfully",
                extra={
                    "user_id": self.user_id,
                },
            )

            return (
                "I successfully checked the official Government of India "
                "PMJDY website during this conversation. "
                f"Here is the relevant information: {result} "
                "Source: official PMJDY website. "
                "The information was retrieved now, so the caller should "
                "still verify important eligibility or documentation "
                "details with the official source or a bank."
            )

        except Exception:
            logger.exception(
                "PMJDY official source lookup failed"
            )

            return (
                "I couldn't reach the official PMJDY information source "
                "right now. I don't want to guess or give you outdated "
                "financial information. Please try again in a moment "
                "or check the official PMJDY website."
            )


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()

    init_database()

    logger.info(
        "BharatMoney memory database ready"
    )


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):

    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    await ctx.connect()

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

        # Deepgram Nova-3
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

        # IMPORTANT:
        # MultilingualModel() was removed because it was producing:
        #
        # AssertionError:
        # end_of_utterance prediction should always returns a result
        #
        # Silero VAD + endpointing handles turn detection here.
        turn_detection=None,

        # Silero VAD
        vad=ctx.proc.userdata["vad"],

        # Faster generation
        preemptive_generation=True,

        # Responsive timing
        min_endpointing_delay=0.3,
        max_endpointing_delay=1.5,

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

    await session.generate_reply(
        instructions=(
            "Start the conversation now. Say the FIRST GREETING from "
            "your instructions. Keep it natural and concise. "
            "Do not call lookup_user, save_user_memory, or "
            "check_pmjdy_information during the first greeting."
        )
    )


if __name__ == "__main__":
    cli.run_app(server)