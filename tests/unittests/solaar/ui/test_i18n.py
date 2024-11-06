import locale
import os
import platform

import pytest

from solaar import i18n


@pytest.fixture
def set_locale_de():
    backup_lang = os.environ.get("LC_ALL", "")
    try:
        yield
    finally:
        os.environ["LC_ALL"] = backup_lang
        i18n.set_locale_to_system_default()


@pytest.mark.skipif(platform.system() == "Linux", reason="Adapt test for Linux")
def test_set_locale_to_system_default(set_locale_de):
    os.environ["LC_ALL"] = "de_DE.UTF-8"
    i18n.set_locale_to_system_default()

    language, encoding = locale.getlocale()

    assert language == "de_DE"
    assert encoding == "UTF-8"
