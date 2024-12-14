__author__ = "Clive Bostock"
__date__ = "2024-11-09"
__description__ = "Module responsible for display to console"

from enum import Enum
from lib.config_manager import ConfigManager
from pathlib import Path
from rich import print
from rich.console import Console

class MsgLvl(Enum):
    info = 1
    warning = 2
    error = 3
    critical = 4
    highlight = 5

class ConsoleMgr:
    def __init__(self, config_file_path: Path):
        self.config_file_path = config_file_path
        self.config_manager = ConfigManager(config_file_path=self.config_file_path)
        colour_console = self.config_manager.bool_config_value(config_section='console',
                                                               config_key='colour_console')
        self.INFO_COLOUR = self.config_manager.config_value(config_section='console', config_key='INFO_COLOUR')
        self.WARN_COLOUR = self.config_manager.config_value(config_section='console', config_key='WARN_COLOUR')
        self.ERR_COLOUR = self.config_manager.config_value(config_section='console', config_key='ERR_COLOUR')
        self.CRIT_COLOUR = self.config_manager.config_value(config_section='console', config_key='CRIT_COLOUR')
        self.HIGH_COLOUR = self.config_manager.config_value(config_section='console', config_key='HIGH_COLOUR')

        no_colour = True if not colour_console else False
        # Create a console without color support
        self.console = Console(no_color=no_colour)

    def print_console(self, text: str, msg_level: MsgLvl = MsgLvl.info):
        """
        Print a message to the console based on its message level.

        :param text: str, The message text to print
        :param msg_level: MsgLevel, The level of the message
        """
        level_methods = {
            MsgLvl.info: self.print_info,
            MsgLvl.warning: self.print_warning,
            MsgLvl.error: self.print_error,
            MsgLvl.critical: self.print_critical,
            MsgLvl.highlight: self.print_highlight
        }

        # Fetch the appropriate method and call it
        print_method = level_methods.get(msg_level)
        if print_method:
            print_method(text)
        else:
            print(f"Unrecognized message level: {msg_level} - {text}")

    def print_highlight(self, text: str):
        self.console.print(f"[{self.HIGH_COLOUR}][INFO]: {text}[/{self.HIGH_COLOUR}]")

    def print_info(self, text: str):
        self.console.print(f"[{self.INFO_COLOUR}][INFO]: {text}[/{self.INFO_COLOUR}]")

    def print_warning(self, text: str):
        self.console.print(f"[{self.WARN_COLOUR}][WARNING]: {text}[/{self.WARN_COLOUR}]")

    def print_error(self, text: str):
        self.console.print(f"[{self.ERR_COLOUR}][ERROR]: {text}[/{self.ERR_COLOUR}]")

    def print_critical(self, text: str):
        self.console.print(f"[{self.CRIT_COLOUR}][CRITICAL]: {text} [/{self.CRIT_COLOUR}]")

if __name__ == "__main__":
    config_file = Path('../config/OraTAPI.ini.sample')
    console_manager = ConsoleMgr(config_file_path=config_file)
    console_manager.print_console(text='Test INFO output', msg_level=MsgLvl.info)
    console_manager.print_console(text='Test WARNING output', msg_level=MsgLvl.warning)
    console_manager.print_console(text='Test ERROR output', msg_level=MsgLvl.error)
    console_manager.print_console(text='Test CRITICAL output', msg_level=MsgLvl.critical)
    console_manager.print_console(text='Test HIGHLIGHT output', msg_level=MsgLvl.highlight)