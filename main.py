__author__ = 'Lev'

from time import sleep
from concurrent.futures import ThreadPoolExecutor
from threading import Thread, Timer

from vk_api.listening import get_long_poll_server, long_polling, process_long_polling_results
from vk_api.sending import send_plain_message
from processing.parser import mock_processor
from util import log
from config import answers_queue, user_attempts, user_spam_warnings


def clear_user_attempts():
    user_attempts.clear()
    user_spam_warnings.clear()


def answers_worker():
    i = 0
    while True:
        # log('checking queue...')
        if answers_queue.empty():
            continue
        if i == 1000:
            i = 0
        if i % 4 == 0:
            sleep(1)
        req = answers_queue._get()
        if req is None:
            continue
        try:
            req.complete()
            # write to db
            log('request fully processed...')
        except Exception as e:
            send_plain_message(req.user_id, 'fatal error')  # label
            log('request sending failed with: ' + str(e))
            # write to db
        answers_queue.task_done()
        i += 1


def main():
    pool = ThreadPoolExecutor(10)
    answers_thread = Thread(target=answers_worker)
    answers_thread.start()
    Timer(5, clear_user_attempts).start()
    server, key, ts = get_long_poll_server()

    while True:
        result = long_polling(server, key, ts)
        if 'failed' in result:
            log('fail in long polling, restarting it...')
            server, key, new_ts_unused = get_long_poll_server()
        else:
            ts = result['ts']
            reqs = process_long_polling_results(result['updates'])
            for req in reqs:
                pass
                pool.submit(mock_processor, req)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        log(str(e))
