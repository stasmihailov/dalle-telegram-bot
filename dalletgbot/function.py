import contextlib
import os
import random

import functions_framework
import openai
import requests


def getenv(key):
    keys = {
        "OPENAI_API_KEY": 'key for accessing dalle api',
        "TG_TOKEN": 'telegram bot token',
    }
    if key not in keys.keys():
        raise f'cannot find key {key} in keys {keys.keys()}'

    return os.getenv(key)


openai.api_key = getenv("OPENAI_API_KEY")
tg_token = getenv("TG_TOKEN")

rand = random.Random()


class Requests:
    @staticmethod
    def generate(query):
        response = openai.Image.create(
            prompt=query,
            n=1,
            size="1024x1024"
        )

        images = [data['url'] for data in response['data']]
        return images


class Responses:
    @staticmethod
    @contextlib.contextmanager
    def pretend_typing(chat_id):
        url = f'https://api.telegram.org/bot{tg_token}/sendChatAction'
        requests.post(url, json={
            'chat_id': chat_id,
            'action': 'typing',
        })
        yield

    @staticmethod
    def send_photo(chat_id, image):
        url = f'https://api.telegram.org/bot{tg_token}/sendPhoto'
        payload = {
            'chat_id': chat_id,
            'photo': image,
        }

        requests.post(url, json=payload)

    @staticmethod
    def send_message(chat_id, text):
        url = f'https://api.telegram.org/bot{tg_token}/sendMessage'
        payload = {
            'chat_id': chat_id,
            'text': text,
        }

        requests.post(url, json=payload)

    @staticmethod
    def answer_inline(query_id, images):
        url = f'https://api.telegram.org/bot{tg_token}/answerInlineQuery'
        payload = {
            'inline_query_id': query_id,
            'results': [{
                type: 'photo',
                id: rand.randint(0, 100_000),
                'photo_url': img,
                'thumb_url': img,
            } for img in images],
        }

        requests.post(url, json=payload)


@functions_framework.http
def generate_images(request):
    do_generate_images(request)


def do_generate_images(request):
    msg = request.get_json()
    print('msg', msg)

    do_generate_images(msg)
    if 'message' in msg and 'text' in msg['message']:
        respond_message(msg)
    elif 'inline_query' in msg and 'query' in msg['inline_query']:
        respond_inline(msg)


def respond_message(msg):
    query = msg['message']['text']
    chat_id = msg['message']['chat']['id']

    if query.startswith('/'):
        respond_command(chat_id, query)
        return

    with Responses.pretend_typing(chat_id):
        images = Requests.generate(query)
        for idx, image in enumerate(images):
            Responses.send_photo(chat_id, image)


def respond_command(chat_id, query):
    if query == '/start' or query == '/help':
        with Responses.pretend_typing(chat_id):
            Responses.send_message(chat_id, "Hello! This bot will generate images using DALL·E 2 based on your queries."
                                            "Simply describe the image you want - for example, you can try typing "
                                            "'sunset' or 'cat'.")
        return


def respond_inline(msg):
    query = msg['inline_query']['query']
    query_id = msg['inline_query']['id']

    if not query:
        return

    images = Requests.generate(query)
    Responses.answer_inline(query_id, images)