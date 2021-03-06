import os
import logging

import psycopg2
import psycopg2.extensions
from pymongo import MongoClient
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, Float, MetaData, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base


logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Задание по Psycopg2
# --------------------------------------------------------------

logger.info("Создаём подключёние к Postgres")
params = {
    "host": os.environ['APP_POSTGRES_HOST'],
    "port": os.environ['APP_POSTGRES_PORT'],
    "user": 'postgres'
}
conn = psycopg2.connect(**params)

# дополнительные настройки
psycopg2.extensions.register_type(
    psycopg2.extensions.UNICODE,
    conn
)
conn.set_isolation_level(
    psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT
)
cursor = conn.cursor()

# ВАШ КОД ЗДЕСЬ
# -------------
# таблица movies_top
# movieId (id фильма), ratings_num(число рейтингов), ratings_avg (средний рейтинг фильма)

sql_str = (
        """
            DROP TABLE IF EXISTS movies_top;
            SELECT movieid, COUNT(rating) AS ratings_num, AVG(rating) AS ratings_avg 
            INTO movies_top
            FROM ratings
            GROUP BY movieid
            HAVING AVG(rating)>3
            ORDER BY movieid;
        """
)

# -------------

cursor.execute(sql_str)
conn.commit()

# Проверка - выгружаем данные
cursor.execute("SELECT * FROM movies_top LIMIT 10")
logger.info(
    "Выгружаем данные из таблицы movies_top: (movieId, ratings_num, ratings_avg)\n{}".format(
        [i for i in cursor.fetchall()])
)
cursor.close()
conn.close()

# Задание по SQLAlchemy
# --------------------------------------------------------------
Base = declarative_base()


class MoviesTop(Base):
    __tablename__ = 'movies_top'

    movieid = Column(Integer, primary_key=True)
    ratings_num = Column(Integer)
    ratings_avg = Column(Float)

    def __repr__(self):
        return "<User(movieid='%s', ratings_num='%s', ratings_avg='%s')>" % (self.movieid, self.ratings_num, self.ratings_avg)


# Создаём сессию

engine = create_engine('postgresql://postgres:@{}:{}'.format(os.environ['APP_POSTGRES_HOST'], os.environ['APP_POSTGRES_PORT']))
Session = sessionmaker(bind=engine)
session = Session()


# --------------------------------------------------------------
# Ваш код здесь
# выберите контент у которого больше 15 оценок (используйте filter)
# и средний рейтинг больше 3.5 (filter ещё раз)
# отсортированный по среднему рейтингу (используйте order_by())
# id такого контента нужно сохранить в массив top_rated_content_ids



top_rated_query = session.query(MoviesTop).filter(MoviesTop.ratings_num>15,
    MoviesTop.ratings_avg>3.5).order_by(MoviesTop.ratings_avg.desc())

logger.info("Выборка из top_rated_query\n{}".format([i for i in top_rated_query.limit(4)]))

top_rated_content_ids = [i[0] for i in top_rated_query.values(MoviesTop.movieid)]


# --------------------------------------------------------------

# Задание по PyMongo
mongo = MongoClient(**{
    'host': os.environ['APP_MONGO_HOST'],
    'port': int(os.environ['APP_MONGO_PORT'])
})

# Получите доступ к коллекции tags
db = mongo["movie"]
tags_collection = db['tags']

# подготовка данных - загружаем текстовый файл
agg_filename = '/data/keywords.tsv'
tag_data = []
if db.tags.count_documents({}) == 0:
    with open(agg_filename, 'r') as f:
        for line in f.readlines():
            movieId, tags = line.strip().split('\t')
            tags = eval(tags)
            for tag in tags:
                tag.update({'movieId': int(movieId)})
                tag_data.append(tag)
    tags_collection.insert_many(tag_data)

# id контента используйте для фильтрации - передайте его в модификатор $in внутри find
# в выборку должны попать теги фильмов из массива top_rated_content_ids
mongo_query = tags_collection.find({'movieId': {'$in': top_rated_content_ids}})
mongo_docs = [i for i in mongo_query]

print("Достали документы из Mongo: {}".format(mongo_docs[:5]))

id_tags = [(i['movieId'], i['name']) for i in mongo_docs]


# Задание по Pandas
# --------------------------------------------------------------
# Постройте таблицу их тегов и определите top-5 самых популярных

# формируем DataFrame
tags_df = pd.DataFrame(id_tags, columns=['movieid', 'tags'])

# --------------------------------------------------------------
# Ваш код здесь
# сгруппируйте по названию тега с помощью group_by
# для каждого тега вычислите, в каком количестве фильмов он встречается
# оставьте top-5 самых популярных тегов
tags_df=tags_df.groupby('tags').count().sort_values(
    'movieid',ascending=False).rename(columns={'movieid':'num_of_films_with_tag'})

top_5_tags = tags_df.head(5)

print(top_5_tags)

logger.info("Домашка выполнена!")
# --------------------------------------------------------------
