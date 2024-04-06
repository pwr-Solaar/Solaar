from solaar.ui.about.model import AboutModel
from solaar.ui.about.presenter import Presenter


def test_about_model():
    expected_name = "Daniel Pavel"
    model = AboutModel()

    authors = model.get_authors()

    assert expected_name in authors[0]


def test_about_dialog(mocker):
    model = AboutModel()
    view = mocker.Mock()
    presenter = Presenter(model, view)

    presenter.run()

    assert view.init_ui.call_count == 1
    assert view.update_version_info.call_count == 1
    assert view.update_description.call_count == 1
    assert view.update_authors.call_count == 1
    assert view.update_credits.call_count == 1
    assert view.update_copyright.call_count == 1
    assert view.update_translators.call_count == 1
    assert view.update_website.call_count == 1
    assert view.show.call_count == 1
