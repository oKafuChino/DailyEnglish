from aiogram.fsm.state import State, StatesGroup


class Review(StatesGroup):
    waiting_for_choice = State()
    waiting_for_spelling = State()
