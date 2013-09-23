#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from .payment import *
from .account import *


def register():
    Pool.register(
        Journal,
        Group,
        Payment,
        MoveLine,
        ProcessPaymentStart,
        module='account_payment', type_='model')
    Pool.register(
        ProcessPayment,
        module='account_payment', type_='wizard')
