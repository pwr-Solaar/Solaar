from solaar import tasks


def run_task():
    print("Hi!")


def test_task_runner(mocker):
    tr = tasks.TaskRunner(name="Testrunner")
    tr.queue.put((run_task, {}, {}))
    # tr.run()
    # tr.stop()
    # assert tr.alive
    # tr.stop()
    # assert not tr.alive
