from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, \
    CallbackQueryHandler, filters
from PIL import Image, ImageDraw, ImageFont
import json
import os
import random
import logging


ASK_GROUP, CHOOSE_ACTION, ASK_DAYS, ASK_MAX_SUBJECTS, ASK_TIMINGS, ASK_DURATION, ASK_BREAK, ASK_SUBJECTS_COUNT = range(
    8)


GROUPS_FILE = "groups.json"

def clear_json_file(file_path=GROUPS_FILE):

    empty_data = {

    }
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(empty_data, file, ensure_ascii=False, indent=4)
    print(f"✅ Данные в файле {file_path} успешно очищены.")


def load_groups():
    if not os.path.exists(GROUPS_FILE):
        with open(GROUPS_FILE, "w", encoding="utf-8") as file:
            json.dump({}, file, ensure_ascii=False, indent=4)

    try:
        with open(GROUPS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            if not isinstance(data, dict):  # Если данные — не словарь, сбросьте их
                logging.error("Ошибка: данные в файле JSON не являются словарём.")
                clear_json_file()
                return {}
            return data
    except (json.JSONDecodeError, ValueError) as e:
        logging.error(f"Ошибка при загрузке JSON: {e}")
        clear_json_file()
        return {}



def save_groups(groups):
    if not isinstance(groups, dict):
        raise ValueError("Ошибка: данные для сохранения должны быть словарём.")
    with open(GROUPS_FILE, "w", encoding="utf-8") as file:
        json.dump(groups, file, ensure_ascii=False, indent=4)




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("📅 Создать расписание"), KeyboardButton("📚 Просмотреть группы")],
        [KeyboardButton("❌ Очистить данные"), KeyboardButton("❓ О боте")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Здравствуйте! Этот бот поможет вам составить расписание на неделю.\nВыберите действие из меню ниже:",
        reply_markup=reply_markup
    )


async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Бот был создан в качестве курсовой работы студентами группы AIN-1-24 Сагынбековой Аймурок, Клеймович Ангелиной и Соловьёвой Яной.\n\n"
        "🔹 Возможности:\n"
        "- Создание расписания\n"
        "- Просмотр расписания\n"
        "- Очистка данных\n\n"
    )


async def clear_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_json_file()
    await update.message.reply_text("Данные успешно очищены.")


async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data

    if action == "view_schedule":
        groups = load_groups()  # Загружаем группы
        group_name = context.user_data.get("group_name")

        if not isinstance(groups, dict):  # Проверяем, что данные групп — это словарь
            await query.edit_message_text("Ошибка: данные групп повреждены.")
            return ConversationHandler.END

        group_data = groups.get(group_name, {})
        if not isinstance(group_data, dict):  # Проверяем данные для конкретной группы
            await query.edit_message_text("Ошибка: данные группы повреждены.")
            return ConversationHandler.END

        schedule = group_data.get("schedule", "Расписание отсутствует.")
        if isinstance(schedule, dict):  # Если расписание — словарь, создаём изображение
            image_path = create_schedule_image(schedule)
            await query.message.reply_photo(photo=open(image_path, "rb"))
            os.remove(image_path)
        else:  # Иначе выводим текст
            await query.edit_message_text(f"Расписание группы '{group_name}':\n{schedule}")

        return ConversationHandler.END


async def view_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    groups = load_groups()
    if not groups:
        await update.message.reply_text("Группы отсутствуют.")
        return

    for group, data in groups.items():
        schedule = data.get("schedule", "Расписание отсутствует.")
        if schedule == "Расписание отсутствует.":
            await update.message.reply_text(f"Группа: {group}\n{schedule}")
        else:
            image_path = create_schedule_image(schedule)
            await update.message.reply_photo(photo=open(image_path, "rb"), caption=f"Группа: {group}")
            os.remove(image_path)


async def time_table(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Введите название группы:")
    return ASK_GROUP


async def get_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    group_name = update.message.text.strip()
    context.user_data["group_name"] = group_name
    groups = load_groups()

    keyboard = [
        [InlineKeyboardButton("Создать расписание", callback_data="create_schedule")],
        [InlineKeyboardButton("Посмотреть расписание", callback_data="view_schedule")],
        [InlineKeyboardButton("Очистить данные", callback_data="clear_data")],  # Кнопка очистки данных
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if group_name not in groups:
        groups[group_name] = {}
        save_groups(groups)

    await update.message.reply_text(f"Группа '{group_name}' выбрана. Что вы хотите сделать?", reply_markup=reply_markup)
    return CHOOSE_ACTION


async def choose_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    if action == "create_schedule":
        await query.edit_message_text("Сколько учебных дней вам нужно?")
        return ASK_DAYS
    elif action == "view_schedule":
        groups = load_groups()
        group_name = context.user_data["group_name"]
        schedule = groups.get(group_name, {}).get("schedule", "Расписание отсутствует.")
        if schedule == "Расписание отсутствует.":
            await query.edit_message_text(f"Расписание группы '{group_name}':\n{schedule}")
        else:
            image_path = create_schedule_image(schedule)
            await query.message.reply_photo(photo=open(image_path, "rb"))
            os.remove(image_path)
        return ConversationHandler.END


async def get_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text)
        if days <= 0:
            raise ValueError("Количество дней должно быть больше нуля.")
        context.user_data['days'] = days
        await update.message.reply_text("Введите максимальное количество предметов в день:")
        return ASK_MAX_SUBJECTS
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите положительное целое число.")
        return ASK_DAYS


async def get_max_subjects(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        max_subjects = int(update.message.text)
        if max_subjects <= 0:
            raise ValueError("Максимальное количество предметов должно быть больше нуля.")
        context.user_data['max_subjects'] = max_subjects
        await update.message.reply_text("Введите время начала и конца занятий в формате '08:00-15:00':")
        return ASK_TIMINGS
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите положительное целое число.")
        return ASK_MAX_SUBJECTS


async def get_timings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        timings = update.message.text.split('-')
        if len(timings) != 2:
            raise ValueError("Введите время в формате '08:00-15:00'.")
        start_time, end_time = timings
        context.user_data['start_time'] = start_time.strip()
        context.user_data['end_time'] = end_time.strip()
        await update.message.reply_text("Сколько минут длится одно занятие?")
        return ASK_DURATION
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное время в формате '08:00-15:00'.")
        return ASK_TIMINGS


async def get_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        duration = int(update.message.text)
        if duration <= 0:
            raise ValueError("Продолжительность занятия должна быть больше нуля.")
        context.user_data['duration'] = duration
        await update.message.reply_text("Сколько минут длится перерыв между занятиями?")
        return ASK_BREAK
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите положительное целое число.")
        return ASK_DURATION


async def get_break(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        break_duration = int(update.message.text)
        if break_duration < 0:
            raise ValueError("Длительность перерыва не может быть отрицательной.")
        context.user_data['break_duration'] = break_duration
        await update.message.reply_text(
            "Введите список предметов и количество занятий для каждого через запятую в формате 'Математика:3, Физика:2':")
        return ASK_SUBJECTS_COUNT
    except ValueError as e:
        await update.message.reply_text(f"Ошибка: {e}\nПопробуйте ещё раз.")
        return ASK_BREAK


async def get_subjects_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        subjects_input = update.message.text.split(',')
        subjects = {}
        for item in subjects_input:
            subject, count = map(str.strip, item.split(':'))
            count = int(count)
            if count <= 0:
                raise ValueError("Количество занятий для каждого предмета должно быть больше нуля.")
            subjects[subject] = count
        context.user_data['subjects'] = subjects
        await update.message.reply_text("Сейчас я сгенерирую расписание...")


        group_name = context.user_data["group_name"]
        schedule = generate_schedule(context.user_data)
        context.user_data["schedule"] = schedule

        groups = load_groups()
        groups[group_name]["schedule"] = schedule
        save_groups(groups)

        image_path = create_schedule_image(schedule)
        await update.message.reply_photo(photo=open(image_path, "rb"))
        os.remove(image_path)

        return ConversationHandler.END
    except ValueError as e:
        await update.message.reply_text(f"Ошибка: {e}\nПопробуйте ещё раз.")
        return ASK_SUBJECTS_COUNT




def generate_schedule(data):
        days = data['days']
        max_subjects = data['max_subjects']
        subjects = data['subjects']
        start_time = data['start_time']
        end_time = data['end_time']
        duration = data['duration']
        break_duration = data['break_duration']
        window_probability = 0.3

        # Создание временных интервалов
        time_slots = []
        start_hour, start_minute = map(int, start_time.split(':'))
        end_hour, end_minute = map(int, end_time.split(':'))
        total_minutes = end_hour * 60 + end_minute - (start_hour * 60 + start_minute)

        while total_minutes >= duration + break_duration:
            start = f"{start_hour:02}:{start_minute:02}"
            start_minute += duration
            if start_minute >= 60:
                start_minute -= 60
                start_hour += 1
            end = f"{start_hour:02}:{start_minute:02}"
            time_slots.append((start, end))

            # Добавление перерыва
            start_minute += break_duration
            if start_minute >= 60:
                start_minute -= 60
                start_hour += 1
            total_minutes -= (duration + break_duration)

        # Генерация расписания по дням
        schedule = {f"День {i + 1}": [] for i in range(days)}

        for day in schedule:
            available_slots = time_slots[:]
            daily_subjects = min(len(available_slots), max_subjects)

            for i in range(daily_subjects):
                # Выбор временного слота
                if not available_slots:
                    break
                slot_index = random.randint(0, len(available_slots) - 1)
                time_slot = available_slots.pop(slot_index)

                # Выбор предмета
                if subjects:
                    subject = random.choice(list(subjects.keys()))
                    schedule[day].append((subject, time_slot[0], time_slot[1]))

                    # Уменьшаем количество занятий
                    subjects[subject] -= 1
                    if subjects[subject] == 0:
                        del subjects[subject]

                # Добавление "окна" с вероятностью
                if i < daily_subjects - 1 and random.random() < window_probability and available_slots:
                    window_slot_index = random.randint(0, len(available_slots) - 1)
                    window_time_slot = available_slots.pop(window_slot_index)
                    schedule[day].append(("Окно", window_time_slot[0], window_time_slot[1]))

            # Сортировка предметов по времени начала
            schedule[day].sort(key=lambda x: x[1])

        return schedule


def create_schedule_image(schedule, file_path="schedule.png"):
        days = len(schedule)
        max_subjects = max(len(subjects) for subjects in schedule.values())

        width = 800
        height = 100 + days * (50 + max_subjects * 40)
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        font_path = "arial.ttf"
        font_size = 18
        font = ImageFont.truetype(font_path, font_size)

        y = 20
        for day, subjects in schedule.items():
            draw.text((20, y), day, fill="black", font=font)
            y += 40
            for subject, start_time, end_time in subjects:
                if subject == "Окно":
                    draw.text((40, y), f"{start_time}-{end_time} | 🕒 Окно", fill="red", font=font)
                else:
                    draw.text((40, y), f"{start_time}-{end_time} | {subject}", fill="black", font=font)
                y += 40
            y += 20

        image.save(file_path)
        return file_path


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог завершён.")
    return ConversationHandler.END


def main():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
    )

    logger = logging.getLogger(__name__)

    try:
        app = Application.builder().token("7889665164:AAGB2w12C2oBu2lbDsOVLgIrZyQ-QyaK0E0").build()


        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.Regex("^📚 Просмотреть группы$"), view_groups))
        app.add_handler(MessageHandler(filters.Regex("^❌\s*Очистить данные\s*$"), clear_data))
        app.add_handler(MessageHandler(filters.Regex("❓ О боте"), info))
        app.add_handler(ConversationHandler(
            entry_points=[MessageHandler(filters.TEXT & filters.Regex(r"^📅\s*Создать расписание\s*$"), time_table)],
            states={
                ASK_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_group)],
                CHOOSE_ACTION: [CallbackQueryHandler(choose_action)],
                ASK_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_days)],
                ASK_MAX_SUBJECTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_max_subjects)],
                ASK_TIMINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_timings)],
                ASK_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_duration)],
                ASK_BREAK: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_break)],
                ASK_SUBJECTS_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_subjects_count)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        ))

        logger.info("Бот запущен.")
        app.run_polling()

    except Exception as e:
        logger.error(f"Ошибка запуска бота: {e}")

if __name__ == "__main__":
    main()
