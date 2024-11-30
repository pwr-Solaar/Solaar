from solaar.ui.about import about
from solaar.ui.about.model import AboutModel


def test_about_model():
    expected_name = "Daniel Pavel"
    model = AboutModel()

    authors = model.get_authors()

    assert expected_name in authors[0]


def test_about_dialog(mocker):
    view_mock = mocker.Mock()

    about.show(view=view_mock)

    assert view_mock.init_ui.call_count == 1
    assert view_mock.update_version_info.call_count == 1
    assert view_mock.update_description.call_count == 1
    assert view_mock.update_authors.call_count == 1
    assert view_mock.update_credits.call_count == 1
    assert view_mock.update_copyright.call_count == 1
    assert view_mock.update_translators.call_count == 1
    assert view_mock.update_website.call_count == 1
    assert view_mock.show.call_count == 1
