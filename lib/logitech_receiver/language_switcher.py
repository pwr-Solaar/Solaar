import logging
import time
from xkbgroup import XKeyboard

logger = logging.getLogger(__name__)


class LanguageSwitcher:
    def __init__(self):
        self.xkb = None
        try:
            self.xkb = XKeyboard()
        except X11Error as e:
            logger.error(f"Cannot initialize XKeyboard: {e}")
        self.previous_language = None

    def get_current_language(self):
        """Gets the current keyboard layout (language)."""
        try:
            return self.xkb.group_symbol
        except Exception as e:
            logger.error(f"Failed to get current keyboard layout: {e}")
            return None

    def remember_language(self, language):
        """Remembers the previous language."""
        self.previous_language = language
        logger.debug(f"Remembered language: {self.previous_language}")

    def switch_language_to_english(self):
        """Switches the keyboard layout to English."""
        try:
            self.xkb.group_symbol = "us"
            logger.debug("Switched keyboard layout to English.")
        except Exception as e:
            logger.error(f"Failed to switch to English layout: {e}")

    def set_previous_language(self):
        if not self.xkb:
            logger.warning("X11 display not accessible. Skipping get_current_language.")
            return None
            
        """Sets the keyboard layout back to the previously remembered language."""
        if self.previous_language:
            try:
                self.xkb.group_symbol = self.previous_language
                logger.debug(f"Restored keyboard layout to {self.previous_language}.")
            except Exception as e:
                logger.error(f"Failed to restore previous layout: {e}")
            finally:
                self.previous_language = None
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
            self.remember_language(current_language)
            self.switch_language_to_english()
