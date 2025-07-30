import os
from datetime import datetime
import logging


class CustomLogger:
    
    def __init__(self, log_dir="logs"):
        # Ensure logs directory exists
        self.logs_dir = os.path.join(os.getcwd(), log_dir)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # create log file with timestamp
        log_file = f"{datetime.now().strftime('%m_%d_%Y_%H-%M-%S')}.log"
        log_path = os.path.join(self.logs_dir, log_file)
        
        # Configure logging
        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s %(name)s (line:%(lineno)d) - %(message)s",
        )
    
    def get_logger(self, name=__file__):
        return logging.getLogger(os.path.basename(name))
    


if __name__ == "__main__":
    # Example usage
    logger = CustomLogger()
    logger = logger.get_logger(__file__)
    logger.info('Custom logger initialized and ready to use.')