# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, time
from typing import List, Dict, Optional, Tuple
import random
import logging
from config import POSTING_SCHEDULE

logger = logging.getLogger(__name__)


class TimeSlotManager:
    """Менеджер временных слотов для постинга"""

    def __init__(self):
        self.schedule = POSTING_SCHEDULE

        # Маппинг дней недели
        self.weekday_map = {
            0: 'monday',
            1: 'tuesday',
            2: 'wednesday',
            3: 'thursday',
            4: 'friday',
            5: 'saturday',
            6: 'sunday'
        }

    def parse_time_string(self, time_str: str) -> time:
        """Парсит строку времени в формате HH:MM"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour=hour, minute=minute)
        except (ValueError, AttributeError):
            raise ValueError(f"Неверный формат времени: {time_str}")

    def get_day_slots(self, weekday: int) -> List[Dict[str, time]]:
        """Получает временные слоты для дня недели (0=понедельник)"""
        day_name = self.weekday_map.get(weekday)
        if not day_name:
            return []

        day_schedule = self.schedule.get(day_name, [])
        slots = []

        for slot in day_schedule:
            try:
                start_time = self.parse_time_string(slot['start'])
                end_time = self.parse_time_string(slot['end'])

                slots.append({
                    'start': start_time,
                    'end': end_time
                })
            except ValueError as e:
                logger.error(f"Ошибка парсинга слота {slot}: {e}")
                continue

        return slots

    def is_time_in_slots(self, check_datetime: datetime) -> bool:
        """Проверяет, попадает ли время в разрешенные слоты"""
        weekday = check_datetime.weekday()
        check_time = check_datetime.time()

        slots = self.get_day_slots(weekday)

        for slot in slots:
            # Обрабатываем случай, когда слот переходит через полночь
            if slot['end'] < slot['start']:
                # Слот вроде 23:00-02:00
                if check_time >= slot['start'] or check_time <= slot['end']:
                    return True
            else:
                # Обычный слот в пределах одного дня
                if slot['start'] <= check_time <= slot['end']:
                    return True

        # Проверяем предыдущий день для слотов через полночь
        prev_day = (check_datetime - timedelta(days=1))
        prev_weekday = prev_day.weekday()
        prev_slots = self.get_day_slots(prev_weekday)

        for slot in prev_slots:
            if slot['end'] < slot['start'] and check_time <= slot['end']:
                return True

        return False

    def get_next_available_slot(self, from_datetime: datetime) -> Optional[datetime]:
        """Находит следующий доступный слот для постинга"""
        current = from_datetime

        # Ищем в течение 7 дней
        for _ in range(7 * 24 * 60):  # Максимум неделя по минутам
            if self.is_time_in_slots(current):
                return current
            current += timedelta(minutes=1)

        return None

    def distribute_posts_in_slots(
            self,
            count: int,
            start_date: datetime,
            days_ahead: int = 7
    ) -> List[datetime]:
        """Распределяет посты равномерно по доступным слотам"""
        if count <= 0:
            return []

        # Собираем все доступные слоты на указанный период
        available_slots = []
        current_date = start_date.date()

        for day_offset in range(days_ahead):
            check_date = current_date + timedelta(days=day_offset)
            weekday = check_date.weekday()
            slots = self.get_day_slots(weekday)

            for slot in slots:
                # Создаем временные точки в слоте
                slot_start = datetime.combine(check_date, slot['start'])
                slot_end = datetime.combine(check_date, slot['end'])

                # Обрабатываем переход через полночь
                if slot['end'] < slot['start']:
                    slot_end += timedelta(days=1)

                # Пропускаем прошедшие слоты
                if slot_end < start_date:
                    continue

                # Добавляем слот в доступные
                available_slots.append({
                    'start': max(slot_start, start_date),
                    'end': slot_end,
                    'duration_minutes': int((slot_end - max(slot_start, start_date)).total_seconds() / 60)
                })

        if not available_slots:
            logger.warning("Нет доступных слотов для распределения постов")
            return []

        # Сортируем слоты по времени
        available_slots.sort(key=lambda x: x['start'])

        # Вычисляем общее время в минутах
        total_minutes = sum(slot['duration_minutes'] for slot in available_slots)

        if total_minutes < count:
            logger.warning(f"Недостаточно времени для распределения {count} постов")

        # Распределяем посты
        distributed_times = []
        interval = max(1, total_minutes // count) if count > 0 else 1

        minutes_passed = 0
        posts_placed = 0

        for slot in available_slots:
            if posts_placed >= count:
                break

            slot_start_minutes = minutes_passed
            slot_end_minutes = minutes_passed + slot['duration_minutes']

            # Размещаем посты в этом слоте
            while posts_placed < count and minutes_passed < slot_end_minutes:
                # Находим позицию в слоте
                position_in_slot = minutes_passed - slot_start_minutes
                post_time = slot['start'] + timedelta(minutes=position_in_slot)

                distributed_times.append(post_time)
                posts_placed += 1
                minutes_passed += interval

            minutes_passed = slot_end_minutes

        # Если не все посты размещены, добавляем оставшиеся в последний слот
        while posts_placed < count and available_slots:
            last_slot = available_slots[-1]
            # Добавляем с небольшим случайным интервалом в конец последнего слота
            random_offset = random.randint(1, min(30, last_slot['duration_minutes'] // 2))
            post_time = last_slot['end'] - timedelta(minutes=random_offset)
            distributed_times.append(post_time)
            posts_placed += 1

        # Перемешиваем для более естественного распределения
        random.shuffle(distributed_times)
        distributed_times.sort()

        logger.info(f"Распределено {len(distributed_times)} постов по слотам")
        return distributed_times

    def get_quick_schedule_time(self, option: str, from_datetime: datetime) -> Optional[datetime]:
        """Получает время для быстрых опций планирования"""
        if option == "30_min":
            target_time = from_datetime + timedelta(minutes=30)
        elif option == "1_hour":
            target_time = from_datetime + timedelta(hours=1)
        elif option == "tomorrow_9am":
            tomorrow = from_datetime.date() + timedelta(days=1)
            target_time = datetime.combine(tomorrow, time(hour=9, minute=0))
        else:
            return None

        # Проверяем, попадает ли в слоты
        if self.is_time_in_slots(target_time):
            return target_time
        else:
            # Находим ближайший доступный слот
            return self.get_next_available_slot(target_time)

    def parse_user_datetime(self, datetime_str: str) -> Optional[datetime]:
        """Парсит дату и время от пользователя в формате ДД.ММ.ГГГГ ЧЧ:ММ"""
        try:
            # Удаляем лишние пробелы
            datetime_str = datetime_str.strip()

            # Пробуем разные форматы
            formats = [
                "%d.%m.%Y %H:%M",
                "%d.%m.%y %H:%M",
                "%d/%m/%Y %H:%M",
                "%d-%m-%Y %H:%M"
            ]

            for fmt in formats:
                try:
                    parsed_dt = datetime.strptime(datetime_str, fmt)
                    # Проверяем, что дата не в прошлом
                    if parsed_dt < datetime.now():
                        logger.warning(f"Указанная дата в прошлом: {parsed_dt}")
                        return None
                    return parsed_dt
                except ValueError:
                    continue

            raise ValueError(f"Не удалось распарсить дату: {datetime_str}")

        except Exception as e:
            logger.error(f"Ошибка парсинга даты '{datetime_str}': {e}")
            return None

    def format_datetime_for_user(self, dt: datetime) -> str:
        """Форматирует дату и время для отображения пользователю"""
        weekdays = [
            "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"
        ]
        weekday_name = weekdays[dt.weekday()]

        return f"{dt.strftime('%d.%m')} ({weekday_name}) в {dt.strftime('%H:%M')}"

    def get_schedule_summary(self) -> str:
        """Возвращает краткое описание расписания для пользователя"""
        summary_lines = []

        day_names = {
            'monday': 'Пн',
            'tuesday': 'Вт',
            'wednesday': 'Ср',
            'thursday': 'Чт',
            'friday': 'Пт',
            'saturday': 'Сб',
            'sunday': 'Вс'
        }

        for day_key, day_name in day_names.items():
            slots = self.schedule.get(day_key, [])
            if slots:
                slot_strs = []
                for slot in slots:
                    slot_strs.append(f"{slot['start']}–{slot['end']}")
                summary_lines.append(f"{day_name}: {' → '.join(slot_strs)}")

        return "\n".join(summary_lines)


# Глобальный экземпляр менеджера слотов
time_slot_manager = TimeSlotManager()