"""
Add initial content types data to database

Revision ID: 001_add_content_types_data
Revises: 6c3bec1ee993_create_initial_tables
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import Integer, String, Text


# revision identifiers, used by Alembic.
revision: str = '001_add_content_types_data'
down_revision: Union[str, None] = '6c3bec1ee993'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Define the content_types table for insertion
    content_types_table = table('content_types',
        column('id', Integer),
        column('code', Text),
        column('name', Text),
        column('description', Text),
        column('cta_strategy', Text)
    )
    
    # Insert initial content types with ON CONFLICT DO NOTHING to avoid errors if they already exist
    op.execute(
        "INSERT INTO content_types (id, code, name, description, cta_strategy) VALUES "
        "(1, 'insights', '🎓 Инсайты', 'Глубокие идеи и проницательные мысли', 'ENGAGE'), "
        "(2, 'transformation', '📖 Трансформация', 'Истории личных изменений и развития', 'ENGAGE'), "
        "(3, 'day_in_life', '🌴 День из жизни', 'Повседневная жизнь и опыт', 'ENGAGE'), "
        "(4, 'questions', '💬 Вопросы', 'Интерактивные вопросы для аудитории', 'ENGAGE'), "
        "(5, 'lifehacks', '📚 Лайфхаки', 'Полезные советы и трюки', 'ENGAGE'), "
        "(6, 'stories', '👥 Истории других', 'Реальные истории и кейсы', 'ENGAGE'), "
        "(7, 'philosophy', '🤔 Философия', 'Размышления и философские идеи', 'ENGAGE'), "
        "(8, 'challenges', '🎯 Челленджи', 'Вызовы и задания для аудитории', 'ENGAGE'), "
        "(9, 'debates', '⚔️ Дебаты', 'Обсуждение противоречивых тем', 'ENGAGE'), "
        "(10, 'reactions', '📢 Реакции', 'Реакции на тренды и события', 'ENGAGE'), "
        "(11, 'motivation', '💪 Мотивация', 'Мотивационные посты и идеи', 'ENGAGE'), "
        "(12, 'earnings', '💰 Заработок', 'Идеи для заработка и финансовой грамотности', 'ENGAGE'), "
        "(13, 'recommendations', '⭐ Рекомендации', 'Рекомендации продуктов, книг, сервисов', 'ENGAGE'), "
        "(14, 'experiments', '🔬 Эксперименты', 'Результаты экспериментов и тестов', 'ENGAGE') "
        "ON CONFLICT (id) DO NOTHING"
    )


def downgrade() -> None:
    # Remove the content types we added
    op.execute("DELETE FROM content_types WHERE id IN (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14)")