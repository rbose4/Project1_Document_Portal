import yaml
from logger import GLOBAL_LOGGER as log
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
       log.error("Failed to load configuration from yaml file", error=str(e))
       raise DocumentPortalException("Failed to load configuration from yaml file", e) from e
    
if __name__ == "__main__":
    # Example usage
    config = load_config()
    print(config)  # Print the loaded configuration for verification