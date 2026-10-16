import asyncio

import discord

from utils.log import log


async def defer(interaction: discord.Interaction, ephemeral: bool = False) -> bool:
    """Acknowledge the interaction; False if it already expired."""
    try:
        await interaction.response.defer(ephemeral=ephemeral)
        return True
    except discord.errors.HTTPException as e:
        log.error(f"Failed to defer interaction: {e}")
        return False


async def reply(interaction: discord.Interaction, *args, **kwargs) -> bool:
    """Send a followup; False if the interaction expired."""
    try:
        await interaction.followup.send(*args, **kwargs)
        return True
    except discord.errors.NotFound as e:
        log.error(f"Failed to send followup: {e}")
        return False


async def _speak(speech, text: str, voice) -> None:
    try:
        await speech.say(text, voice=voice)
    except Exception as e:
        log.exception(f"Speech failed: {e}")


async def reply_and_speak(
    interaction: discord.Interaction,
    speech,
    text: str | None = None,
    *,
    speak: str | bool | None = None,
    voice="random",
    **send_kwargs,
) -> bool:
    """Send the followup and speak at the same time.

    `speak` is the text to say: defaults to `text`, False means stay silent.
    Neither side can block or break the other.
    """
    to_say = text if speak is None else speak
    sent, _ = await asyncio.gather(
        reply(interaction, text, **send_kwargs),
        _speak(speech, to_say, voice) if to_say else asyncio.sleep(0),
    )
    return sent
