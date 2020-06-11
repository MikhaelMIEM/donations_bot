import requests
import random
import re
from html2text import html2text


def filter_comment(comment):
    comment = html2text(comment)
    comment = re.sub('\[[^\]]+\]\(/po[^\)]+\)', '', comment)
    return comment


def po_random_comment():
    page1 = requests.get('https://2ch.hk/po/1.json').json()
    threads = page1['threads']
    thread_num = random.choice(threads)['thread_num']
    thread = requests.get(
            f'https://2ch.hk/makaba/mobile.fcgi?task=get_thread&board=po&thread={thread_num}&post=0'
            ).json()
    comment = random.choice(thread)['comment']
    filtered_comment = filter_comment(comment)
    return filtered_comment
