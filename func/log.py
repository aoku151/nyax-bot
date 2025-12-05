import logging

def get_log(name:str):
    log = ExceptionLoggerAdapter(logging.getLogger(name), {})
    log.setLevel(level=logging.DEBUG)
    return log

class ExceptionLoggerAdapter(logging.LoggerAdapter):
    def error(self, msg, *args, **kwargs):
        kwargs.setdefault("exc_info", True)
        super().error(msg, *args, **kwargs)
    def warning(self, msg, *args, **kwargs):
        kwargs.setdefault("exc_info", True)
        super().error(msg, *args, **kwargs)

stream_handler = logging.StreamHandler()
logging.getLogger("realtime._async.channel").setLevel(logging.WARNING)
logging.getLogger("realtime._async.client").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
