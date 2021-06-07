from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Text, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

ban_servers = Table('ban_servers', Base.metadata,
                    Column('ban_id', BigInteger, ForeignKey('bans.id')),
                    Column('server_id', BigInteger, ForeignKey('servers.id'))
                    )


class Ban(Base):
    __tablename__ = 'bans'  # if you use base it is obligatory

    id = Column(BigInteger, primary_key=True)  # obligatory
    banned_by = Column(BigInteger)
    reason = Column(Text)
    servers = relationship(
        "Server",
        secondary=ban_servers,
        back_populates="bans")


    def __repr__(self):  # optional
        return f'bans {self.id}'


class Server(Base):
    __tablename__ = 'servers'  # if you use base it is obligatory

    id = Column(BigInteger, primary_key=True)  # obligatory
    channel_id = Column(BigInteger)
    reason = Column(Text)
    bans = relationship(
        "Ban",
        secondary=ban_servers,
        back_populates="servers")

    def __repr__(self):  # optional
        return f'servers {self.id}'


def start():
    engine = create_engine('mysql://root:root@127.0.0.1:3306/tcl', echo=True)
    # engine = create_engine('sqlite:///:memory:', echo=True)
    # engine = create_engine('sqlite:///:memory:')

    Session = sessionmaker(bind=engine, autoflush=True)
    session = Session()

    Base.metadata.create_all(engine)
    return engine, session

# ban_server_table = Table(
#     "ban_server",
#     metadata,
#     Column('id', Integer, primary_key=True),
#     Column('server_id', ForeignKey('servers.id'), nullable=False),
#     Column('ban_id', ForeignKey('bans.id'), nullable=False),
# )
