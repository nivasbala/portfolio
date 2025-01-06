import logging
from datetime import datetime, timezone
from pythonjsonlogger import jsonlogger

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('timestamp'):
            # this doesn't use record.created, so it is slightly off
            now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ')
            log_record['timestamp'] = now
        if log_record.get('level'):
            log_record['severity'] = log_record['severity'].upper()
        else:
            log_record['severity'] = record.levelname


def getJSONLogger(name):
    logger = logging.getLogger(name)
    streamHandler = logging.StreamHandler()
    # fileHandler = logging.FileHandler('app.log')

    ddFormat = ('%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] '
                '[dd.service=%(dd.service)s dd.env=%(dd.env)s dd.version=%(dd.version)s dd.trace_id=%(dd.trace_id)s dd.span_id=%(dd.span_id)s] '
                '- %(message)s')

    streamFormatter = CustomJsonFormatter(ddFormat)
    # fileFormatter = CustomJsonFormatter(ddFormat)

    streamHandler.setFormatter(streamFormatter)
    # fileHandler.setFormatter(fileFormatter)

    logger.addHandler(streamHandler)
    # logger.addHandler(fileHandler)

    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def setup_logger(logger_name='app-logger'):
    logger = getJSONLogger(logger_name)
    logging.basicConfig(level=logging.INFO)
    return logger


# Setup Logger with JSON and include traceid
logger = setup_logger('llm-agent-logger')
