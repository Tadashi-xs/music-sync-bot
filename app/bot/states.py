from aiogram.fsm.state import State, StatesGroup

class States(StatesGroup):
    waiting_add = State()
    waiting_delete = State()
