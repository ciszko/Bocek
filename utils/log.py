import logging
import logging.handlers

import discord


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    blue = "\x1b[36;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    pink = "\x1b[35;1m"
    green = "\x1b[32:20m"
    reset = "\x1b[0m"
    date = blue + "%(asctime)s " + reset
    msg = f"{pink} [%(filename)s:%(lineno)d]{reset} %(message)s"

    FORMATS = {
        logging.DEBUG: date + grey + "%(levelname)-8s" + msg,
        logging.INFO: date + green + "%(levelname)-8s" + msg,
        logging.WARNING: date + yellow + "%(levelname)-8s" + msg,
        logging.ERROR: date + red + "%(levelname)-8s" + msg,
        logging.CRITICAL: date + bold_red + "%(levelname)-8s" + msg,
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, self.datefmt)
        return formatter.format(record)


dt_fmt = "%Y-%m-%d %H:%M:%S"
discord.utils.setup_logging(formatter=CustomFormatter(datefmt=dt_fmt))
log = logging.getLogger("discord")
