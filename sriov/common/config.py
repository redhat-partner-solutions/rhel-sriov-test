import yaml


class Config:
    def __init__(self, config_file: str, testbed_file: str) -> None:
        """Init the config file object

        Args:
            self:
            config_file (str): path to the config file
            testbed_file (str): path to the testbed file
        """
        with open(config_file, "r") as file:
            self.config = yaml.safe_load(file)
        with open(testbed_file, "r") as file:
            testbed = yaml.safe_load(file)
            for k, v in testbed.items():
                self.config[k] = v       
