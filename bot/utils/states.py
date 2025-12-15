from aiogram.fsm.state import State, StatesGroup

class UserStates(StatesGroup):
    """Состояния пользователя в боте"""
    
    # Основные состояния
    main_menu = State()
    guest_menu = State()
    pro_menu = State()
    
    # Турист - воронка
    tourist_menu = State()
    tourist_why_cheaper = State()
    tourist_legal = State()
    tourist_example = State()
    tourist_consultant = State()
    
    # Новые состояния для ветки путешествий
    travel_branch_selection = State()
    travel_pay_less = State()
    travel_5star_3star = State()
    travel_more = State()
    
    # Партнер - воронка
    partner_qualification = State()
    
    # Ветка 1: Пассивный доход
    partner_passive_income = State()
    partner_passive_income_scheme = State()
    partner_passive_income_final = State()
    
    # Ветка 2: Путешествовать бесплатно
    partner_travel_free = State()
    partner_travel_free_how = State()
    partner_travel_free_final = State()
    
    # Ветка 3: Уволиться из найма
    partner_quit_job = State()
    partner_quit_job_plan = State()
    partner_quit_job_final = State()
    
    # PRO настройки и персонализация
    settings_menu = State()
    personalization_menu = State()
    awaiting_welcome_video = State()
    awaiting_pay_less_voice = State()
    awaiting_5star_3star_voice = State()
    awaiting_travel_more_voice = State()
    awaiting_passive_income_voice = State()
    awaiting_passive_income_final_voice = State()
    awaiting_free_travel_voice = State()
    awaiting_free_travel_final_voice = State()
    awaiting_final_voice = State()
    awaiting_quit_job_voice = State()
    awaiting_quit_job_final_voice = State()
    awaiting_freedom_voice = State()
    
    # Радар
    radar_view = State()
    
    # AI-Designer
    ai_designer_active = State()
    ai_designer_awaiting_replay_photo = State()  # Ожидание фото для replay из истории
    
    # AI-Тренажер возражений
    ai_trainer_menu = State()
    ai_trainer_library = State()
    ai_trainer_active = State()  # Активная тренировка
    ai_trainer_awaiting_voice = State()  # Ожидание голосового от пользователя
    
    # Контент-Мейкер
    content_maker_main = State()  # Главное меню контент-мейкера
    content_maker_planner = State()  # Планер идей
    content_maker_personalization = State()  # Настройки персонализации

class ContentMakerStates(StatesGroup):
    """Состояния модуля Контент-Мейкер"""
    
    # Заполнение профиля
    profile_fill_choice = State()  # Выбор способа заполнения (текст/голос)
    profile_fill_text = State()  # Ожидание текста
    profile_fill_voice = State()  # Ожидание голосовых сообщений
    profile_view = State()  # Просмотр профиля
    
    # Генерация идей
    idea_select_type = State()  # Выбор типа контента
    idea_select_platform = State()  # Выбор платформы
    idea_generated = State()  # Идеи сгенерированы, ожидание выбора
    idea_custom_input = State()  # Ожидание своей идеи текстом
    
    # Написание постов
    post_select_source = State()  # Выбор источника (идеи/планер/своя)
    post_select_from_planner = State()  # Выбор идеи из планера
    post_custom_idea = State()  # Ожидание своей идеи для поста
    post_viewing = State()  # Просмотр сгенерированного поста
    post_editing = State()  # Редактирование поста (ожидание инструкции)
    
    # Планер
    planner_viewing = State()  # Просмотр планера
    planner_search = State()  # Поиск в планере