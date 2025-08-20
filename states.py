# -*- coding: utf-8 -*-
from aiogram.fsm.state import State, StatesGroup


class Menu(StatesGroup):
    """Состояния главного меню"""
    main = State()


class PostCreation(StatesGroup):
    """Состояния создания поста"""
    waiting = State()      # Ожидание контента от пользователя
    scheduling = State()   # Выбор времени публикации


class QueueView(StatesGroup):
    """Состояния просмотра очереди"""
    viewing = State()      # Просмотр списка отложенных постов


class Settings(StatesGroup):
    """Состояния настроек"""
    main = State()              # Главное меню настроек
    editing_prompt = State()    # Редактирование промпта
    changing_admin = State()    # Смена админа
    changing_group = State()    # Смена группы