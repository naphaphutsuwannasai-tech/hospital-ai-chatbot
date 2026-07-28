import logging
from logging.handlers import RotatingFileHandler

log_formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log_handler = RotatingFileHandler("chat.log", maxBytes=5*1024*1024, backupCount=3, encoding="utf-8")
log_handler.setFormatter(log_formatter)

app_logger = logging.getLogger("HospitalAIChat")
app_logger.setLevel(logging.INFO)
app_logger.addHandler(log_handler)

def log_question(question, source):
    app_logger.info(f"({source}) {question}")

def log_error(error_msg):
    app_logger.error(error_msg)
