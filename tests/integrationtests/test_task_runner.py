from solaar import tasks


def run_task():
    print("Hi!")


def test_task_runner(mocker):
    tr = tasks.TaskRunner(name="Testrunner")
    tr.start()
    assert tr.alive

    tr(run_task)

    tr.stop()
    assert not tr.alive
