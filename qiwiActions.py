import requests
import json
import datetime


def invoice(pay_id, value, qiwi_cash_secret_key):
    expiration_date = datetime.datetime.today() + datetime.timedelta(days=730)
    expiration_date_time_str = expiration_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")

    headers = {
        'authorization': 'Bearer ' + qiwi_cash_secret_key
    }
    parameters = {
        "amount": {
            "currency": "RUB",
            "value": "{:.2f}".format(value)
        },
        "expirationDateTime": expiration_date_time_str
    }
    response = requests.put('https://api.qiwi.com/partner/bill/v1/bills/' + str(pay_id),
                            json=parameters,
                            headers=headers)
    return json.loads(response.text)['payUrl']


def pay_status(pay_id, qiwi_cash_secret_key):
    headers = {
        'authorization': 'Bearer ' + qiwi_cash_secret_key
    }
    response = requests.get('https://api.qiwi.com/partner/bill/v1/bills/' + str(pay_id), json={}, headers=headers)
    return json.loads(response.text)['status']['value']
