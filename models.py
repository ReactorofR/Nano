from sqlalchemy import ForeignKey, Integer, String, Table,UniqueConstraint,create_engine,Column,and_,func
from sqlalchemy.orm import relationship,sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.sqltypes import NullType
from sqlalchemy.ext.declarative import declarative_base

import os

engine = create_engine('sqlite:///db.sqlite3')
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()
metadata = Base.metadata

association_table = Table('girldatabase_qtanimegirl_tags',Base.metadata,
    Column('qtanimegirl_id', Integer, ForeignKey('girldatabase_qtanimegirl.id'), nullable=False, index=True),
    Column('tag_id', Integer, ForeignKey('girldatabase_tag.id'), nullable=False, index=True)
)

class QtAnimeGirl(Base):
    __tablename__ = 'girldatabase_qtanimegirl'

    id = Column(Integer, primary_key=True)
    name = Column(String(40), default= '')
    elo = Column(Integer, nullable=False, default= 1000)
    image = Column(String(100), nullable=False, unique= True)

    tags = relationship(
        "Tag",
        secondary = association_table,
        back_populates = "qtanimegirls")

    def __str__(self):
        if self.name is not None and self.name > '':
            return self.name
        else:
            return str(self.id)

    def get_all_girls(self,path='/images/'):
        for path in os.listdir(path):
            a = QtAnimeGirl(image=path)
            Session.add(a)
        session.commit()

    def get_new_girls(self,path='/images/'):
        new_girl_count = 0
        for image in os.listdir(path):
            try:
                a = session.query(QtAnimeGirl).filter(QtAnimeGirl.image==image).one()
            except NoResultFound:
                print('Adding new girl with image {}'.format(image))
                a = QtAnimeGirl(image=image)
                session.add(a)
                new_girl_count += 1
        session.commit()
        return new_girl_count

    def updateELO(self,eloOpponent,score):
        expectedA = 1/(1+pow(10,((eloOpponent-self.elo)/400)))
        self.elo = round(self.elo + 32 * (score-expectedA))
        session.commit()

    def addTag(self,tag):
        try:
            tag = session.query(QtAnimeGirl).filter(and_ (QtAnimeGirl.tags.any(tag = tag),QtAnimeGirl.id == self.id)).one()
        except NoResultFound:
            try:
                new_tag = session.query(Tag).filter(Tag.tag == tag).one()
            except NoResultFound:
                new_tag = Tag(tag=tag)
                session.add(new_tag)
            self.tags.append(new_tag)
            session.commit()



class Tag(Base):
    __tablename__ = 'girldatabase_tag'

    id = Column(Integer, primary_key=True)
    tag = Column(String(50), nullable=False)

    qtanimegirls = relationship(
        "QtAnimeGirl",
        secondary = association_table,
        back_populates = "tags")

    def __str__(self):
        return self.tag

t_sqlite_sequence = Table(
    'sqlite_sequence', metadata,
    Column('name', NullType),
    Column('seq', NullType)
)
