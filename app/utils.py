import slack
from aiotasks import AsyncTaskDelayBase

async def send_task(task_name, args=None, manager=None, **kwargs):
    if not manager:
        manager = current_app()

    assert isinstance(manager, AsyncTaskDelayBase)

    # Get function name
    try:
        fn_name = manager.task_available_tasks[task_name]
    except KeyError:
        raise ValueError("Function doesn't exist")

    if not args:
        args = tuple()

    # Get task
    task = partial(manager.context_class,
                   fn_name,
                   manager.task_list_name,
                   manager.poller,
                   task_name,
                   manager._loop_delay)

    return await task(*args, **kwargs)

def slack_notify(config, msg, **kwargs):
    client = slack.WebClient(
        token=config['SLACK_API_TOKEN'],
        loop=kwargs.get('loop', False),
        run_async=kwargs.get('run_async', False),
    )
    response = client.chat_postMessage(
        channel=config.get('SLACK_CHANNEL', kwargs.get('slack_channel', '#ebay')),
        text=msg)
