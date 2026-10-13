from datetime import datetime


class MoodSystem:
    _HAPPY_THRESHOLD = 33
    _GRUMPY_THRESHOLD = -33
    _NATURAL_DECAY = 3
    _IDLE_PENALTY = 10
    _IDLE_SECONDS = 5 * 60

    def __init__(self) -> None:
        self._score: int = 0
        self.last_positive: datetime = datetime.now()

    @property
    def mood(self) -> str:
        if self._score > self._HAPPY_THRESHOLD:
            return "happy"
        if self._score < self._GRUMPY_THRESHOLD:
            return "grumpy"
        return "neutral"

    def adjust(self, delta: int) -> None:
        self._score = max(-100, min(100, self._score + delta))
        if delta > 0:
            self.last_positive = datetime.now()

    def decay(self, *, in_voice: bool) -> None:
        """Natural decay toward neutral + idle penalty when in voice."""
        if self._score > 0:
            self._score = max(0, self._score - self._NATURAL_DECAY)
        elif self._score < 0:
            self._score = min(0, self._score + self._NATURAL_DECAY)

        if in_voice:
            idle = (datetime.now() - self.last_positive).total_seconds()
            if idle > self._IDLE_SECONDS:
                self._score = max(-100, self._score - self._IDLE_PENALTY)
