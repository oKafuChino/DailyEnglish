from aiogram.fsm.state import State, StatesGroup


class UserSettings(StatesGroup):
    waiting_for_push_time = State()
    waiting_for_timezone = State()
