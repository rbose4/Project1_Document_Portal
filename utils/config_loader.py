import yaml
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException
import sys

def load_config(config_path:str = "config/config.yaml") -> dict:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path (str): Path to the YAML configuration file.
        
    Returns:
        dict: Configuration data as a dictionary.
    """
    try:
        with open(config_path, 'r') as file:
            config = yaml.safe_load(file)
        return config
    except Exception as e:
        app_exc = DocumentPortalException(e, sys) # type: ignore
        logger = CustomLogger().get_logger(__file__)
        logger.error(app_exc)
        raise app_exc
    
if __name__ == "__main__":
    # Example usage
    config = load_config()
    print(config)  # Print the loaded configuration for verification