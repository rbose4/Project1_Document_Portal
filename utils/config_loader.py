import yaml

def load_config(config_path:str = "config/config.yaml") -> dict:
    """
    Load configuration from a YAML file.
    
    Args:
        config_path (str): Path to the YAML configuration file.
        
    Returns:
        dict: Configuration data as a dictionary.
    """
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

if __name__ == "__main__":
    # Example usage
    config = load_config()
    print(config)  # Print the loaded configuration for verification