import logging
import subprocess

from xkbgroup import X11Error
from xkbgroup import XKeyboard

logger = logging.getLogger(__name__)


# it would be better to use xkbgroup to switch language, but I don't know how to work with it
class LanguageSwitcher:
    def __init__(self):
        self.xkb = None
        try:
            self.xkb = XKeyboard()
        except X11Error as e:
            logger.error(f"Cannot initialize XKeyboard: {e}")
        self.previous_layout = None

    def get_current_layout(self):
        """Gets the current keyboard layout (language)."""
        try:
            result = subprocess.run(["setxkbmap", "-query"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "layout:" in line:
                    return line.split(":")[1].strip()
        except Exception as e:
            logger.error(f"Failed to get current keyboard layout: {e}")
            return None

    def get_current_language(self):
        """Gets the current keyboard layout (language)."""
        try:
            # xkb used because setxkbmap shows only layout, but not language. So we need to use xkb to check current language
            return self.xkb.group_symbol
        except Exception as e:
            logger.error(f"Failed to get current keyboard layout: {e}")
            return None

    def remember_layout(self, language):
        """Remembers the previous language."""
        self.previous_layout = language
        logger.debug(f"Remembered language: {self.previous_layout}")

    # switch to english using setxkbmap because xkbgroup switching seems to be asynctounous and I don't know how work with it
    # you can use xkbgroup to switch to english. just remember previous_language instead of layout
    # and use self.xkb.group_symbol =  "us", self.xkb.group_symbol = previous_language
    def switch_language_to_english(self):
        """Switches the keyboard layout to English."""
        try:
            subprocess.run(["setxkbmap", "us"], check=True)
            logger.debug("Switched keyboard layout to English.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to switch to English layout: {e}")

    def set_previous_language(self):
        """Sets the keyboard layout back to the previously remembered language."""
        if self.previous_layout:
            try:
                subprocess.run(["setxkbmap", self.previous_layout], check=True)
                logger.debug(f"Restored keyboard layout to {self.previous_layout}.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to restore previous layout: {e}")
            finally:
                self.previous_layout = None
        else:
            logger.warning("No previous language was remembered.")

    def evaluate(self):
        """Evaluate the current language and switch to English if it's not already English."""
        if not self.xkb:
            logger.warning("X11 display not accessible. Skipping get_current_language.")
            return None

        current_language = self.get_current_language()
        logger.debug(f"Current language: {current_language}")

        if current_language != "us":
            current_layout = self.get_current_layout()
            logger.debug(f"Current layout: {current_layout}")
            self.remember_layout(current_layout)
            self.switch_language_to_english()
