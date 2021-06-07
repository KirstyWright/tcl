# import sqlite3
import sqlalchemy
import os
from sqlalchemy import MetaData, Table, Column, Integer, String, Text, ForeignKey

class Storage(object):
    """docstring for Storage."""
    connection = None
    engine = None

    def __init__(self):
        self.engine = sqlalchemy.create_engine("sqlite+pysqlite:///:memory:", echo=True, future=True)
        self.connection = self.engine.connect();

    def __del__(self):
        if self.connection:
            self.connection.close()

    def select_multiple(self, statement, parameters=[]):
        return self.query(statement, parameters).fetchall()

    def query(self, statement, parameters=[]):
        """ run a query from statement on the connection object
        :param statement: a sql statement
        :return:
        """
        # try:
        result = self.connection.execute(sqlalchemy.text(statement), parameters)
        self.connection.commit()
        return result
        # except Error as e:
        #     print("SQL ERROR")
        #     print(e)

    def setup(self):
        metadata = MetaData()
        ban_table = Table(
            "bans",
            metadata,
            Column('id', Integer, primary_key=True),
            Column('banned_by', Integer),
            Column('reason', Text)
        )
        server_table = Table(
            "servers",
            metadata,
            Column('id', Integer, primary_key=True),
            Column('channel_id', Integer),
        )
        ban_server_table = Table(
            "ban_server",
            metadata,
            Column('id', Integer, primary_key=True),
            Column('server_id', ForeignKey('servers.id'), nullable=False),
            Column('ban_id', ForeignKey('bans.id'), nullable=False),
        )
        metadata.create_all(self.engine);
