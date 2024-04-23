import logging
import subprocess

logger = logging.getLogger(__name__)


class LanguageSwitcher:
    def __init__(self):
        self.previous_language = None

    def get_current_language(self):
        """Gets the current keyboard layout (language)."""
        try:
            result = subprocess.run(["setxkbmap", "-query"], capture_output=True, text=True)
            for line in result.stdout.splitlines():
                if "layout:" in line:
                    return line.split(":")[1].strip()
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
            subprocess.run(["setxkbmap", "us"], check=True)
            logger.debug("Switched keyboard layout to English.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to switch to English layout: {e}")

    def set_previous_language(self):
        """Sets the keyboard layout back to the previously remembered language."""
        if self.previous_language:
            try:
                subprocess.run(["setxkbmap", self.previous_language], check=True)
                logger.debug(f"Restored keyboard layout to {self.previous_language}.")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to restore previous layout: {e}")
            finally:
                self.previous_language = None
        else:
            logger.warning("No previous language was remembered.")

    def evaluate(self):
        """Evaluate the current language and switch to English if it's not already English."""
        current_language = self.get_current_language()
        logger.debug(f"Current language: {current_language}")

        if current_language and current_language != "us":
            self.remember_language(current_language)
            self.switch_language_to_english()
