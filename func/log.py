import logging

def get_log(name:str):
  log = logging.getLogger(name)
  log.setLevel(level=logging.DEBUG)
  return log
stream_handler = logging.StreamHandler()
logging.getLogger("realtime._async.channel").setLevel(logging.WARNING)
logging.getLogger("realtime._async.client").setLevel(logging.WARNING)
