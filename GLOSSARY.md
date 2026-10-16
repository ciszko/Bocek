# Glossary

**Speech**: Turning text into audio and playing it in the bot's voice channel. One module owns synthesis, voice connection, playback and temp-file cleanup. Callers decide *whether* to speak; Speech decides *how*.

**Fart**: The audio clip (randomly pitched, stretched and echoed from `farts/`) played by `/pierd`, and played in place of speech when synthesis fails.
