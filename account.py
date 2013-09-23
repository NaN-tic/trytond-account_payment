#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
from sql.aggregate import Sum
from sql.conditionals import Case, Coalesce
from sql.operators import Abs

from trytond.pool import Pool, PoolMeta
from trytond.model import fields
from trytond.pyson import Eval, If, Bool

from .payment import KINDS

__metaclass__ = PoolMeta
__all__ = ['MoveLine']


class MoveLine:
    __name__ = 'account.move.line'
    payment_amount = fields.Function(fields.Numeric('Payment Amount',
            digits=(16,
                If(Bool(Eval('second_currency_digits')),
                    Eval('second_currency_digits', 2),
                    Eval('currency_digits', 2))),
            states={
                'invisible': ~Eval('payment_kind'),
                },
            depends=['payment_kind']), 'get_payment_amount',
        searcher='search_payment_amount')
    payments = fields.One2Many('account.payment', 'line', 'Payments',
        readonly=True,
        states={
            'invisible': ~Eval('payment_kind'),
            },
        depends=['payment_kind'])
    payment_kind = fields.Function(fields.Selection([
                (None, ''),
                ] + KINDS, 'Payment Kind'), 'get_payment_kind',
        searcher='search_payment_kind')

    @classmethod
    def get_payment_amount(cls, lines, name):
        amounts = {}
        for line in lines:
            if line.account.kind not in ('payable', 'receivable'):
                amounts[line.id] = None
                continue
            if line.second_currency:
                amount = abs(line.amount_second_currency)
            else:
                amount = abs(line.credit - line.debit)

            for payment in line.payments:
                if payment.state != 'failed':
                    amount -= payment.amount

            amounts[line.id] = amount
        return amounts

    @classmethod
    def search_payment_amount(cls, name, clause):
        pool = Pool()
        Payment = pool.get('account.payment')
        Account = pool.get('account.account')
        _, operator, value = clause
        Operator = fields.SQL_OPERATORS[operator]
        table = cls.__table__()
        payment = Payment.__table__()
        account = Account.__table__()
        query_table = table.join(payment, type_='LEFT', condition=(
                (table.id == payment.line) & (payment.state != 'failed'))
        ).join(account, condition=table.account == account.id)
        main_payable = (table.credit - table.debit) - Sum(
            Coalesce(payment.amount, 0))
        main_receivable = (table.debit - table.credit) - Sum(
            Coalesce(payment.amount, 0))
        second_payable = (
            table.amount_second_currency * Abs(table.debit - table.credit)
            / (table.debit - table.credit)) - Sum(Coalesce(payment.amount, 0))
        seconde_receivable = (
            table.amount_second_currency * Abs(table.credit - table.debit)
            / (table.credit - table.debit)) - Sum(Coalesce(payment.amount, 0))
        query = query_table.select(table.id,
            where=account.kind.in_(['payable', 'receivable']),
            group_by=(table.id, account.kind, table.second_currency),
            having=Operator(
                Case((table.second_currency == None,
                        Case((account.kind == 'payable', main_payable),
                            else_=main_receivable)),
                    else_=Case((account.kind == 'payable', second_payable),
                        else_=seconde_receivable)),
                getattr(cls, name).sql_format(value)))
        return [('id', 'in', query)]

    def get_payment_kind(self, name):
        return self.account.kind if self.account.kind in dict(KINDS) else None

    @classmethod
    def search_payment_kind(cls, name, clause):
        return [('account.kind',) + tuple(clause[1:])]

    @classmethod
    def copy(cls, lines, default=None):
        if default is None:
            default = {}
        else:
            default = default.copy()
        default.setdefault('payments', None)
        return super(MoveLine, cls).copy(lines, default=default)
