from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey, Boolean, DateTime
from datetime import datetime


class Db:
    WAITING = 'WAITING'
    PAID = 'PAID'
    REJECTED = 'REJECTED'
    EXPIRED = 'EXPIRED'

    def __init__(self):
        self.__engine = create_engine('sqlite:///bot.db', echo=True)
        self.__create_tables()
        self.__conn = self.__engine.connect()
        self.__insert_payment_statuses()

    def __create_tables(self):
        meta = MetaData()

        self.__Payment_status = Table(
            'Payment_status', meta,
            Column('kind', String, primary_key=True, unique=True)
        )

        self.__Person = Table(
            'Person', meta,
            Column('id', Integer, primary_key=True),
            Column('is_donater', Boolean)
        )

        self.__Payment = Table(
            'Payment', meta,
            Column('id', Integer, primary_key=True, autoincrement=True),
            Column('amount', Integer),
            Column('url', String),
            Column('person', Integer, ForeignKey('Person.id')),
            Column('date', DateTime(timezone=True), default=datetime.now()),
            Column('payment_status', String, ForeignKey('Payment_status.kind'))
        )

        self.__Monthly_payment_mailing = Table(
            'Monthly_payment_mailing', meta,
            Column('month', Integer, default=datetime.now().month, primary_key=True),
            Column('year', Integer, default=datetime.now().year, primary_key=True),
            Column('happened', Boolean, default=False)
        )

        meta.create_all(self.__engine)

    def __insert_payment_statuses(self):
        payment_statuses = [self.WAITING, self.PAID, self.REJECTED, self.EXPIRED]
        for status in payment_statuses:
            sel = self.__Payment_status.select().where(self.__Payment_status.c.kind == status)
            if not list(self.__conn.execute(sel)):
                ins = self.__Payment_status.insert().values(kind=status)
                self.__conn.execute(ins)

    def get_person(self, id):
        sel = self.__Person.select().where(self.__Person.c.id == id)
        data = list(self.__conn.execute(sel))
        return data[0] if data else None

    def insert_person(self, id, is_donater=False):
        ins = self.__Person.insert().values(id=id, is_donater=is_donater)
        self.__conn.execute(ins)

    def insert_payment(self, person_id, amount, url, payment_status='WAITING'):
        date = datetime.now()
        ins = self.__Payment.insert().values(person=person_id, amount=amount, url=url, payment_status=payment_status,
                                             date=date)
        return self.__conn.execute(ins).lastrowid, date

    def update_payment_status(self, payment_id, status):
        upd = self.__Payment.update().where(self.__Payment.c.id == payment_id).values(payment_status=status)
        self.__conn.execute(upd)

    def update_donater_status(self, person_id, is_donater):
        upd = self.__Person.update().where(self.__Person.c.id == person_id).values(is_donater=is_donater)
        self.__conn.execute(upd)

    def select_person_debt(self, person_id):
        sel = self.__Payment.select().where(self.__Payment.c.person == person_id).where(
            self.__Payment.c.payment_status == self.WAITING)
        return self.__conn.execute(sel)

    def select_donaters(self):
        sel = self.__Person.select().where(self.__Person.c.is_donater == True)
        return self.__conn.execute(sel)

    def did_person_get_invoice_this_month(self, person_id):
        today = datetime.today()
        sel = self.__Payment.select().where(self.__Payment.c.person == person_id).where(
            self.__Payment.c.date >= datetime(today.year, today.month, 1))
        return bool(list(self.__conn.execute(sel)))

    def get_new_payment_id(self):
        sel = self.__Payment.select()
        payments = self.__conn.execute(sel)
        id_list = [payment['id'] for payment in payments]
        if id_list:
            return max(id_list) + 1
        else:
            return 1

    def insert_mailing(self, month=datetime.now().month, year=datetime.now().year, happened=False):
        ins = self.__Monthly_payment_mailing.insert().values(month=month, year=year, happened=happened)
        self.__conn.execute(ins)

    def is_mailing_exist(self, month, year):
        sel = self.__Monthly_payment_mailing.select().where(self.__Monthly_payment_mailing.c.month == month).where(
            self.__Monthly_payment_mailing.c.year == year
        )
        return bool(list(self.__conn.execute(sel)))

    def update_mailing_happened_status(self, month, year, happened):
        upd = self.__Monthly_payment_mailing.update().where(self.__Monthly_payment_mailing.c.month == month).where(
            self.__Monthly_payment_mailing.c.year == year
        ).values(happened=happened)
        self.__conn.execute(upd)

    def did_mailing_happen(self, month, year):
        sel = self.__Monthly_payment_mailing.select().where(self.__Monthly_payment_mailing.c.month == month).where(
            self.__Monthly_payment_mailing.c.year == year
        )
        return self.__conn.execute(sel)[0]['happened']