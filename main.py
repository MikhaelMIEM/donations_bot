import vk_api
from vk_api.utils import get_random_id
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
import json
from Db import Db
from qiwiActions import invoice, pay_status
from datetime import datetime
from time import sleep
from threading import Thread

with open('config.json') as config:
    conf_data = json.load(config)
QIWI_SECRET = conf_data['qiwi_cash_secret_key']

vk_session = vk_api.VkApi(token=conf_data['vk_api_token'])
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, conf_data['vk_group_id'])

donate_amount = 10

months = ['', 'январь', 'февраль', 'март', 'апрель', 'май', 'июнь', 'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь',
          'декабрь']


def answer_vk_message(event, text):
    vk.messages.send(
        random_id=get_random_id(),
        user_id=event.message['peer_id'],
        message=text
    )


def send_vk_message(person_id, text):
    vk.messages.send(
        random_id=get_random_id(),
        user_id=person_id,
        message=text
    )


def become_donator(db, event):
    id = event.message['peer_id']
    person = db.get_person(id)
    answer = 'Подписка на ежемесячные уведомления о взносах успешно оформлена'
    if not person:
        db.insert_person(id, True)
    else:
        if person['is_donater'] is False:
            db.update_donater_status(id, True)
        else:
            answer = 'Вы уже подписаны на уведомления о взносах'
    answer_vk_message(event, answer)
    if not db.did_person_get_invoice_this_month(id):
        answer = form_new_payment(db, id, donate_amount)
        answer_vk_message(event, answer)


def stop_being_donator(db, event):
    id = event.message['peer_id']
    person = db.get_person(id)
    answer = 'Вы не подписаны на уведомления о взносах'
    if person:
        if person['is_donater'] is True:
            db.update_donater_status(id, False)
            answer = 'Подписка на ежемесячные уведомления о взносах прекращена(('
    answer_vk_message(event, answer)


def show_debt(db, event):
    id = event.message['peer_id']
    person = db.get_person(id)
    if not person:
        answer = 'Вы не подписаны на получение уведомлений о взносах. \n' + \
                 'Для того, чтобы стать жертвователем, наберите команду donate'
    else:
        update_person_payments_statuses(db, id)
        debts = list(db.select_person_debt(id))
        if not debts:
            answer = 'У вас нет неоплаченных долгов :)'
        else:
            debt_urls = [debt['url'] for debt in debts]
            answer = 'Текущие долги: \n' + \
                     '\n'.join([debt_url for debt_url in debt_urls])
    answer_vk_message(event, answer)


def update_person_payments_statuses(db, id):
    debts = db.select_person_debt(id)
    for debt in debts:
        payment_id = debt['id']
        if pay_status(payment_id, QIWI_SECRET) == db.PAID:
            db.update_payment_status(payment_id, db.PAID)


def send_invoice():
    pass


def send_command_list(event):
    answer = """
Список команд бота:
    
𝐃𝐨𝐧𝐚𝐭𝐞 - получать ежемесячные уведомления о взносах
𝐒𝐭𝐨𝐩 𝐝𝐨𝐧𝐚𝐭𝐞 - отписаться от ежемесячных уведомлений о взносах
𝐃𝐞𝐛𝐭 - проверить наличие долгов по взносам
    """
    answer_vk_message(event, answer)


def send_monthly_notification_to_donaters(db):
    donaters = db.select_donaters()
    for donater in donaters:
        id = donater['id']
        if not db.did_person_get_invoice_this_month(id):
            message = form_new_payment(db, id, donate_amount)
            send_vk_message(id, message)

        update_person_payments_statuses(db, id)
        debts = list(db.select_person_debt(id))
        if debts:
            debt_urls = [debt['url'] for debt in debts]
            message = 'И не забываем про долги =) \n' + '\n'.join([debt_url for debt_url in debt_urls])
            send_vk_message(id, message)


def form_new_payment(db, person_id, donate_amount):
    payment_id = db.get_new_payment_id()
    invoice_url = invoice(payment_id, donate_amount, QIWI_SECRET)
    _, date = db.insert_payment(person_id, donate_amount, invoice_url)
    answer = 'Платежка за ' + months[date.month] + ' ' + str(date.year) + '\n' + invoice_url
    return answer


def bot_main():
    db = Db()
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_NEW:
            if event.from_user:
                if event.message['text'].lower() == 'donate':
                    become_donator(db, event)
                elif event.message['text'].lower() == 'stop donate':
                    stop_being_donator(db, event)
                elif event.message['text'].lower() == 'debt':
                    show_debt(db, event)
                elif event.message['text'].lower() == 'invoice123':
                    send_invoice()
                else:
                    send_command_list(event)


def mailing():
    db = Db()
    last_mailing_month = 0
    while True:
        now = datetime.now()
        if last_mailing_month != now.month and now.hour >= 20:
            if not db.is_mailing_exist(now.month, now.year):
                send_monthly_notification_to_donaters(db)
                db.insert_mailing(now.month, now.year, True)
            last_mailing_month = now.month
        sleep(1800)


if __name__ == '__main__':
    thread_pool = {
        'chat_bot': Thread(target=bot_main),
        'mailing': Thread(target=mailing)
    }

    for thread in thread_pool:
        thread_pool[thread].start()

    while True:
        sleep(10)
        for thread in thread_pool:
            if not thread_pool[thread].is_alive():
                if thread == 'chat_bot':
                    thread_pool[thread] = Thread(target=bot_main)
                if thread == 'mailing':
                    thread_pool[thread] = Thread(target=mailing)
                thread_pool[thread].start()
