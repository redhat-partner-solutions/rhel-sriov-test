import yaml

class Config:
    def __init__(self, config_file):
        """ Init the config file object

        Args:
            self:              ssh_obj to the remote host
            config_file (str): path to the config file
        """
        with open(config_file, 'r') as file:
            self.config = yaml.safe_load(file)
