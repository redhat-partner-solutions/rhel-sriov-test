import typing
import yaml


class Config:
    def __init__(self, config_file: str) -> None:
        """ Init the config file object

        Args:
            self:
            config_file (str): path to the config file
        """
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)
