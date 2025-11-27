import logging

def get_log(name:str):
  log = logging.getLogger(name)
  log.setLevel(level=logging.DEBUG)
  return log
stream_hancler = logging.StreamHandler()
logging.getLogger("realtime")
