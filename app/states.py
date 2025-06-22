from aiogram.fsm.state import State, StatesGroup


class RegExample(StatesGroup):
    name = State()
    number = State()
    location = State()


class AdminOrderStates(StatesGroup):
    EnterTrackingNumber = State()
