import logging


logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - [%(levelname)s] - %(message)s',
)

logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)

logger = logging.getLogger('app')
logger.setLevel(logging.DEBUG)
