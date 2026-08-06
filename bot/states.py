from aiogram.fsm.state import State, StatesGroup


class TransactionFlow(StatesGroup):
    clarifying = State()
    offset_decision = State()
    confirming = State()
    waiting_repayment_name = State()
