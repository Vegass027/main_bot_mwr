from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

# Главное меню для гостей
def get_guest_menu() -> InlineKeyboardMarkup:
    """Меню для новых пользователей (статус FREE)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏖 Путешествия", callback_data="tourist")],
        [InlineKeyboardButton(text="💼 Бизнес", callback_data="partner")]
    ])

# Главное меню для PRO пользователей
def get_pro_menu() -> InlineKeyboardMarkup:
    """Панель инструментов для PRO пользователей"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🤖 AI-Наставник", callback_data="ai_mentor"),
            InlineKeyboardButton(text="🗺 Трэвел-Архитектор", callback_data="travel_architect")
        ],
        [
            InlineKeyboardButton(text="✍️ Контент-Мейкер", callback_data="content_maker"),
            InlineKeyboardButton(text="🎨 AI-Дизайнер", callback_data="ai_designer")
        ],
        [
            InlineKeyboardButton(text="🥊 Тренажер", callback_data="trainer"),
            InlineKeyboardButton(text="🧮 Калькулятор", callback_data="calculator")
        ],
        [
            InlineKeyboardButton(text="🎨 Персонализация воронки", callback_data="personalization"),
            InlineKeyboardButton(text="🕵️ Радар", callback_data="radar")
        ],
        [
            InlineKeyboardButton(text="🔗 Моя реферальная ссылка", callback_data="my_referral_link")
        ],
        [
            InlineKeyboardButton(text="🏢 МОЙ ОФИС", web_app=WebAppInfo(url="https://clubsmarttravel.vercel.app/"))
        ]
    ])

# Меню туриста
def get_tourist_menu() -> InlineKeyboardMarkup:
    """Меню вопросов для туриста"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📉 Почему дешевле?", callback_data="tourist_why_cheaper")],
        [InlineKeyboardButton(text="⚖️ Легально ли это?", callback_data="tourist_legal")],
        [InlineKeyboardButton(text="💎 Пример экономии", callback_data="tourist_example")],
        [InlineKeyboardButton(text="👤 Связаться с консультантом", callback_data="tourist_consultant")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# Новое меню выбора ветки путешествий
def get_travel_branch_menu() -> InlineKeyboardMarkup:
    """Меню выбора ветки путешествий"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📉 Платить меньше", callback_data="travel_pay_less")],
        [InlineKeyboardButton(text="👑 Жить в 5★ по цене 3★", callback_data="travel_5star_3star")],
        [InlineKeyboardButton(text="🌍 Путешествовать чаще", callback_data="travel_more")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# Подменю туриста с возвратом
def get_tourist_back_menu() -> InlineKeyboardMarkup:
    """Кнопка возврата в меню туриста"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="tourist")]
    ])

# Меню партнера - квалификация
def get_partner_qualification_menu() -> InlineKeyboardMarkup:
    """Меню выбора приоритета для партнера"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Пассивный доход", callback_data="partner_passive_income")],
        [InlineKeyboardButton(text="🌍 Путешествовать бесплатно", callback_data="partner_travel_free")],
        [InlineKeyboardButton(text="🚀 Уволиться из найма", callback_data="partner_quit_job")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# Промежуточные кнопки для партнёрских веток
def get_partner_passive_income_button() -> InlineKeyboardMarkup:
    """Промежуточная кнопка для ветки Пассивный доход"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📉 Показать схему дохода", callback_data="partner_show_income_scheme")]
    ])

def get_partner_travel_free_button() -> InlineKeyboardMarkup:
    """Промежуточная кнопка для ветки Путешествовать бесплатно"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✈️ Как начать летать бесплатно?", callback_data="partner_show_travel_how")]
    ])

def get_partner_quit_job_button() -> InlineKeyboardMarkup:
    """Промежуточная кнопка для ветки Уволиться из найма"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 План побега из найма", callback_data="partner_show_quit_plan")]
    ])

# Финальные кнопки с WebApp для каждой ветки
def get_partner_passive_income_final() -> InlineKeyboardMarkup:
    """Финальная кнопка для ветки Пассивный доход"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Открыть Модель Дохода", web_app=WebAppInfo(url="https://wmrlifenew1.vercel.app/"))],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

def get_partner_travel_free_final() -> InlineKeyboardMarkup:
    """Финальная кнопка для ветки Путешествовать бесплатно"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Забрать доступ к Платформе", web_app=WebAppInfo(url="https://wmrlifenew1.vercel.app/"))],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main")]
    ])

# ========== КОНТЕНТ-МЕЙКЕР КЛАВИАТУРЫ ==========

def get_content_maker_profile_choice(show_back: bool = False) -> InlineKeyboardMarkup:
    """Выбор способа заполнения профиля"""
    buttons = [
        [
            InlineKeyboardButton(text="🎙 Голос", callback_data="cm_profile_voice"),
            InlineKeyboardButton(text="📝 Текст", callback_data="cm_profile_text")
        ]
    ]
    
    if show_back:
        buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cm_personalization")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_content_maker_voice_session() -> InlineKeyboardMarkup:
    """Кнопки управления голосовой сессией"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎤 Записать ещё", callback_data="cm_voice_continue")],
        [InlineKeyboardButton(text="💾 Завершить и сохранить", callback_data="cm_voice_finish")]
    ])

def get_content_maker_main_menu() -> InlineKeyboardMarkup:
    """Главное меню контент-мейкера"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💡 Придумать идеи", callback_data="cm_generate_ideas")],
        [InlineKeyboardButton(text="📝 Написать на свою тему", callback_data="cm_write_custom_post")],
        [InlineKeyboardButton(text="📋 Написать из планера", callback_data="cm_write_from_planner")],
        [InlineKeyboardButton(text="⚙️ Настройки персонализации", callback_data="cm_personalization")],
        [InlineKeyboardButton(text="◀️ Назад в меню PRO", callback_data="back_to_pro")]
    ])

def get_content_maker_profile_view() -> InlineKeyboardMarkup:
    """Кнопки просмотра профиля"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Перезаписать профиль", callback_data="cm_profile_rewrite")],
        [InlineKeyboardButton(text="👀 Посмотреть полностью", callback_data="cm_profile_view_full")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="cm_main")]
    ])

def get_content_types_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора типа контента (15 типов)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎓 Инсайты", callback_data="cm_type_1"),
            InlineKeyboardButton(text="📖 Трансформация", callback_data="cm_type_2")
        ],
        [
            InlineKeyboardButton(text="🌴 День из жизни", callback_data="cm_type_3"),
            InlineKeyboardButton(text="💬 Вопросы", callback_data="cm_type_4")
        ],
        [
            InlineKeyboardButton(text="📚 Лайфхаки", callback_data="cm_type_5"),
            InlineKeyboardButton(text="👥 Истории других", callback_data="cm_type_6")
        ],
        [
            InlineKeyboardButton(text="🤔 Философия", callback_data="cm_type_7"),
            InlineKeyboardButton(text="🎯 Челленджи", callback_data="cm_type_8")
        ],
        [
            InlineKeyboardButton(text="⚔️ Дебаты", callback_data="cm_type_9"),
            InlineKeyboardButton(text="📢 Реакции", callback_data="cm_type_10")
        ],
        [
            InlineKeyboardButton(text="💪 Мотивация", callback_data="cm_type_11"),
            InlineKeyboardButton(text="💰 Заработок", callback_data="cm_type_12")
        ],
        [
            InlineKeyboardButton(text="⭐ Рекомендации", callback_data="cm_type_13"),
            InlineKeyboardButton(text="🔬 Эксперименты", callback_data="cm_type_14")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="cm_main")]
    ])

def get_platform_keyboard() -> InlineKeyboardMarkup:
    """Выбор платформы"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Telegram", callback_data="cm_platform_telegram")],
        [InlineKeyboardButton(text="📸 Instagram", callback_data="cm_platform_instagram")],
        [InlineKeyboardButton(text="🧵 Threads", callback_data="cm_platform_threads")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="cm_generate_ideas")]
    ])

def get_idea_navigation_keyboard(current_index: int, total_ideas: int) -> InlineKeyboardMarkup:
    """Клавиатура навигации по идеям"""
    buttons = []
    
    # Кнопки действий с идеей
    action_buttons = [
        InlineKeyboardButton(text="💾 Сохранить", callback_data=f"cm_save_idea_{current_index}"),
        InlineKeyboardButton(text="📝 Выбрать", callback_data=f"cm_select_idea_{current_index}")
    ]
    buttons.append(action_buttons)
    
    # Кнопки навигации
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"cm_idea_nav_{current_index-1}"))
    
    # Показываем текущую позицию
    nav_buttons.append(InlineKeyboardButton(
        text=f"{current_index + 1}/{total_ideas}",
        callback_data="cm_idea_position"
    ))
    
    if current_index < total_ideas - 1:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"cm_idea_nav_{current_index+1}"))
    
    buttons.append(nav_buttons)
    
    # Кнопка "Назад"
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cm_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_idea_action_keyboard(idea_index: int) -> InlineKeyboardMarkup:
    """Кнопки действий для одной идеи (устаревшая, оставлена для совместимости)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💾 Сохранить", callback_data=f"cm_save_idea_{idea_index}"),
            InlineKeyboardButton(text="📝 Выбрать", callback_data=f"cm_select_idea_{idea_index}")
        ]
    ])

def get_ideas_bottom_keyboard() -> InlineKeyboardMarkup:
    """Нижние кнопки для списка идей"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Своя идея (напиши текст)", callback_data="cm_custom_idea")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="cm_main")]
    ])

def get_post_source_keyboard() -> InlineKeyboardMarkup:
    """Выбор источника для написания поста"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💡 Из идей", callback_data="cm_post_from_generated")],
        [InlineKeyboardButton(text="📋 Из планера", callback_data="cm_post_from_planner")],
        [InlineKeyboardButton(text="✏️ Своя идея", callback_data="cm_post_custom_idea")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="cm_main")]
    ])

def get_post_actions_keyboard(post_id: str) -> InlineKeyboardMarkup:
    """Действия с постом"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Копировать", callback_data=f"cm_copy_post_{post_id}"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"cm_edit_post_{post_id}")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад в меню", callback_data="cm_main")
        ]
    ])

def get_planner_idea_actions(idea_id: str) -> InlineKeyboardMarkup:
    """Действия с идеей в планере"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Написать", callback_data=f"cm_write_from_idea_{idea_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"cm_delete_idea_{idea_id}")
        ]
    ])

def get_planner_categories_keyboard(categories: dict) -> InlineKeyboardMarkup:
    """
    Клавиатура категорий планера с количеством идей
    
    Args:
        categories: Словарь {content_type_id: (name, count)}
    """
    buttons = []
    
    # Маппинг эмодзи для типов контента
    type_emojis = {
        1: "🎓", 2: "📖", 3: "🌴", 4: "💬", 5: "📚",
        6: "👥", 7: "🤔", 8: "🎯", 9: "⚔️", 10: "📢",
        11: "💪", 12: "💰", 13: "⭐", 14: "🔬"
    }
    
    # Создаем кнопки для каждой категории
    for type_id, (name, count) in sorted(categories.items()):
        emoji = type_emojis.get(type_id, "📝")
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {name} ({count})",
                callback_data=f"cm_planner_type_{type_id}"
            )
        ])
    
    # Кнопка "Назад"
    buttons.append([InlineKeyboardButton(text="🔙 Назад", callback_data="cm_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_planner_type_ideas_keyboard(
    current_index: int,
    total_ideas: int,
    idea_id: str,
    type_id: int
) -> InlineKeyboardMarkup:
    """Клавиатура навигации по идеям в категории планера"""
    buttons = []
    
    # Кнопки действий с идеей
    action_buttons = [
        InlineKeyboardButton(text="📝 Написать", callback_data=f"cm_write_from_idea_{idea_id}"),
        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"cm_delete_idea_{idea_id}")
    ]
    buttons.append(action_buttons)
    
    # Кнопки навигации
    nav_buttons = []
    if current_index > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="⬅️", callback_data=f"cm_planner_nav_{type_id}_{current_index-1}")
        )
    
    # Показываем текущую позицию
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{current_index + 1}/{total_ideas}",
            callback_data="cm_planner_position"
        )
    )
    
    if current_index < total_ideas - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="➡️", callback_data=f"cm_planner_nav_{type_id}_{current_index+1}")
        )
    
    buttons.append(nav_buttons)
    
    # Кнопка "Назад к категориям"
    buttons.append([InlineKeyboardButton(text="🔙 К категориям", callback_data="cm_planner")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_planner_keyboard(total_ideas: int, page: int = 0) -> InlineKeyboardMarkup:
    """Клавиатура планера с пагинацией (устаревшая, оставлена для совместимости)"""
    buttons = []
    
    # Кнопки навигации если идей больше 10
    if total_ideas > 10:
        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton(text="◀️ Назад", callback_data=f"cm_planner_page_{page-1}"))
        if (page + 1) * 10 < total_ideas:
            nav_buttons.append(InlineKeyboardButton(text="Вперёд ▶️", callback_data=f"cm_planner_page_{page+1}"))
        
        if nav_buttons:
            buttons.append(nav_buttons)
    
    # Кнопка поиска и возврат
    buttons.append([InlineKeyboardButton(text="🔍 Поиск", callback_data="cm_planner_search")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="cm_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_to_content_maker() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню контент-мейкера"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="cm_main")]
    ])

# ========== AI-ТРЕНАЖЕР КЛАВИАТУРЫ ==========

def get_ai_trainer_menu() -> InlineKeyboardMarkup:
    """Главное меню AI-тренажера"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📚 Библиотека соперников", callback_data="trainer_library")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="trainer_stats")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_pro_menu")]
    ])

def get_opponent_list_keyboard(opponents: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком соперников"""
    keyboard = []
    
    # Добавляем кнопку для каждого соперника
    for opp in opponents:
        keyboard.append([
            InlineKeyboardButton(
                text=opp['name'],
                callback_data=f"trainer_opponent_{opp['id']}"
            )
        ])
    
    # Кнопка назад
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="trainer_menu")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_opponent_card_keyboard(opponent_id: str) -> InlineKeyboardMarkup:
    """Клавиатура карточки соперника"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🥊 Начать", callback_data=f"trainer_start_{opponent_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="trainer_library")]
    ])

def get_training_confirm_keyboard(opponent_id: str) -> InlineKeyboardMarkup:
    """Подтверждение начала тренировки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да, начать!", callback_data=f"trainer_confirm_{opponent_id}")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data=f"trainer_opponent_{opponent_id}")]
    ])

def get_training_active_keyboard(session_id: str) -> InlineKeyboardMarkup:
    """Клавиатура во время активной тренировки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏹ Завершить тренировку", callback_data=f"trainer_end_{session_id}")]
    ])

def get_training_results_keyboard(opponent_id: str = None) -> InlineKeyboardMarkup:
    """Клавиатура после завершения тренировки"""
    keyboard = []
    
    if opponent_id:
        keyboard.append([InlineKeyboardButton(
            text="🔄 Пройти снова",
            callback_data=f"trainer_opponent_{opponent_id}"
        )])
    
    keyboard.extend([
        [InlineKeyboardButton(text="📚 Другой соперник", callback_data="trainer_library")],
        [InlineKeyboardButton(text="📊 Моя статистика", callback_data="trainer_stats")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="trainer_menu")]
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_partner_quit_job_final() -> InlineKeyboardMarkup:
    """Финальная кнопка для ветки Уволиться из найма"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔐 Получить Пошаговый План", web_app=WebAppInfo(url="https://wmrlifenew1.vercel.app/"))],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])

# Меню персонализации воронки
def get_personalization_menu(
    has_welcome: bool,
    has_pay_less_voice: bool,
    has_5star_3star_voice: bool,
    has_travel_more_voice: bool,
    has_passive_income_voice: bool,
    has_passive_income_final_voice: bool,
    has_free_travel_voice: bool,
    has_free_travel_final_voice: bool,
    has_quit_job_voice: bool,
    has_quit_job_final_voice: bool
) -> InlineKeyboardMarkup:
    """Меню персонализации воронки с индикаторами статусов"""
    welcome_status = "✅" if has_welcome else "❌"
    pay_less_status = "✅" if has_pay_less_voice else "❌"
    five_star_status = "✅" if has_5star_3star_voice else "❌"
    travel_more_status = "✅" if has_travel_more_voice else "❌"
    passive_income_status = "✅" if has_passive_income_voice else "❌"
    passive_income_final_status = "✅" if has_passive_income_final_voice else "❌"
    free_travel_status = "✅" if has_free_travel_voice else "❌"
    free_travel_final_status = "✅" if has_free_travel_final_voice else "❌"
    quit_job_status = "✅" if has_quit_job_voice else "❌"
    quit_job_final_status = "✅" if has_quit_job_final_voice else "❌"
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"📹 КРУЖОК (Приветствие) {welcome_status}",
            callback_data="upload_welcome_video"
        )],
        [InlineKeyboardButton(
            text=f"📉 Платить меньше {pay_less_status}",
            callback_data="upload_pay_less_voice"
        )],
        [InlineKeyboardButton(
            text=f"👑 Жить в 5★ по цене 3★ {five_star_status}",
            callback_data="upload_5star_3star_voice"
        )],
        [InlineKeyboardButton(
            text=f"🌍 Путешествовать чаще {travel_more_status}",
            callback_data="upload_travel_more_voice"
        )],
        [InlineKeyboardButton(
            text=f"💸 Пассивный доход {passive_income_status}",
            callback_data="upload_passive_income_voice"
        )],
        [InlineKeyboardButton(
            text=f"💸 Пассивный доход 2️⃣ {passive_income_final_status}",
            callback_data="upload_passive_income_final_voice"
        )],
        [InlineKeyboardButton(
            text=f"🌍 Путешествовать бесплатно {free_travel_status}",
            callback_data="upload_free_travel_voice"
        )],
        [InlineKeyboardButton(
            text=f"🌍 Путешествовать бесплатно 2️⃣ {free_travel_final_status}",
            callback_data="upload_free_travel_final_voice"
        )],
        [InlineKeyboardButton(
            text=f"🚀 Уволиться из найма {quit_job_status}",
            callback_data="upload_quit_job_voice"
        )],
        [InlineKeyboardButton(
            text=f"🚀 Уволиться из найма 2️⃣ {quit_job_final_status}",
            callback_data="upload_quit_job_final_voice"
        )],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="back_to_pro_menu")]
    ])
# AI-Designer постоянная панель управления
def get_ai_designer_control_panel() -> InlineKeyboardMarkup:
    """Постоянная панель управления AI-Designer (всегда внизу)"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📜 История", callback_data="ai_designer_history"),
            InlineKeyboardButton(text="💡 Примеры", callback_data="ai_designer_examples")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_pro")
        ]
    ])

# AI-Designer меню при входе
def get_ai_designer_menu() -> InlineKeyboardMarkup:
    """Меню AI-Designer при входе"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📜 История генераций", callback_data="ai_designer_history")],
        [InlineKeyboardButton(text="💡 Примеры запросов", callback_data="ai_designer_examples")],
        [InlineKeyboardButton(text="◀️ Назад в PRO", callback_data="back_to_pro")]
    ])


# Кнопка возврата в главное меню
def get_back_to_main_menu() -> InlineKeyboardMarkup:
    """Универсальная кнопка возврата в главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад в меню", callback_data="back_to_main")]
    ])

# Кнопка возврата в PRO меню
def get_back_to_pro_menu() -> InlineKeyboardMarkup:
    """Кнопка возврата в PRO меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_pro_menu")]
    ])

# Кнопка возврата к персонализации
def get_back_to_personalization() -> InlineKeyboardMarkup:
    """Кнопка возврата к меню персонализации"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="personalization")]
    ])