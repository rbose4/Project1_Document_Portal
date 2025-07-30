import os
from datetime import datetime
import logging
import structlog


class CustomLogger:
    
    # def __init__(self, log_dir="logs"):
    #     # Ensure logs directory exists
    #     self.logs_dir = os.path.join(os.getcwd(), log_dir)
    #     os.makedirs(self.logs_dir, exist_ok=True)
        
    #     # create log file with timestamp
    #     log_file = f"{datetime.now().strftime('%m_%d_%Y_%H-%M-%S')}.log"
    #     log_path = os.path.join(self.logs_dir, log_file)
        
    #     # Configure logging
    #     logging.basicConfig(
    #         filename=log_path,
    #         level=logging.INFO,
    #         format="[%(asctime)s] %(levelname)s %(name)s (line:%(lineno)d) - %(message)s",
    #     )
    
    # def get_logger(self, name=__file__):
    #     return logging.getLogger(os.path.basename(name))
    
    def __init__(self, log_dir="logs"):
        #Ensure logs directory exists
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        log_file = f"{datetime.now().strftime('%m_%d_%Y_%H-%M-%S')}.log"
        self.log_path = os.path.join(self.logs_dir, log_file)
        
    def get_logger(self, name=__file__):
        logger_name = os.path.basename(name)
        
        #configure logging for console and file (both JSON)
        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(logging.Formatter('%(message)s'))     # Only message logged, no timestamp or level
        
        # set up console handler for console outpu
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter('%(message)s'))  # Only message logged, no timestamp or level
        
        logging.basicConfig(
            handlers=[file_handler, console_handler],
            level=logging.INFO,
            format='%(message)s'  # Structlog will handle the JSON formatting
        )
        
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt='iso', utc=True, key='timestamp'),
                structlog.processors.add_log_level,
                structlog.processors.EventRenamer(to='event'),
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
        return structlog.get_logger(logger_name)

if __name__ == "__main__":
    # Example usage
    # logger = CustomLogger()
    # logger = logger.get_logger(__file__)
    # logger.info('Custom logger initialized and ready to use.')
    
    logger = CustomLogger().get_logger(__file__)
    logger.info("Custom logger initialized and ready to use.", user_id=12345, filename="report.pdf")
    logger.error("An error occurred while processing the file.", user_id=12345, filename="report.pdf", error="File not found")
    