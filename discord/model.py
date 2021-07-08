from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Text, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

Base = declarative_base()

# ban_servers = Table('ban_servers', Base.metadata,
#                     Column('ban_id', BigInteger, ForeignKey('bans.id')),
#                     Column('server_id', BigInteger, ForeignKey('servers.id')),
#                     Column('status', String),
#                     Column('message_id', BigInteger)
#                     )
# SqlConnection

class BanServer(Base):
    __tablename__ = 'ban_servers'
    ban_id = Column(BigInteger, ForeignKey('bans.id'), primary_key=True)
    server_id = Column(BigInteger, ForeignKey('servers.id'), primary_key=True)
    status = Column(String(length=20))
    message_id = Column(BigInteger)

    server = relationship("Server", back_populates="bans")
    ban = relationship("Ban", back_populates="servers")


class Ban(Base):
    __tablename__ = 'bans'  # if you use base it is obligatory

    id = Column(BigInteger, primary_key=True)  # obligatory
    banned_by = Column(BigInteger)
    reason = Column(Text)
    evidence = Column(Text)
    tarkov = Column(String(length=256))
    status = Column(Integer, default=0)
    servers = relationship("BanServer", back_populates="ban")

    # status
    # 100 inactive (initialised and awaiting tarkov name)
    # 101 inactive (initialised and awaiting ban reason)
    # 102 inactive (initialised and awaiting ban evidence)
    # 103 inactive (awaiting ban approval)
    # 1 active

    def __repr__(self):  # optional
        return f'bans {self.id}'


class Server(Base):
    __tablename__ = 'servers'  # if you use base it is obligatory

    id = Column(BigInteger, primary_key=True)  # obligatory
    channel_id = Column(BigInteger)
    bans = relationship("BanServer", back_populates="server")

    def __repr__(self):  # optional
        return f'servers {self.id}'


def start():
    engine = create_engine(config['DEFAULT']['SqlConnection'], echo=True)

    Session = sessionmaker(bind=engine, autoflush=True)
    session = Session()

    Base.metadata.create_all(engine)
    return engine, session


result = start()
engine = result[0]
session = result[1]
