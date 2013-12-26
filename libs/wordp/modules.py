from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import dict4ini
CONF = dict4ini.DictIni('/etc/wordp.ini')
MYSQL_USER = CONF.weixin.mysql_user
MYSQL_PASS = CONF.weixin.mysql_pass
MYSQL_HOST = CONF.weixin.mysql_host
MYSQL_DBNAME = CONF.weixin.mysql_dbname
MYSQL_TABLE_PRE = CONF.weixin.mysql_table_pre

DB_CONNECT_STRING = \
'mysql+mysqldb://%(user)s:%(pass)s@%(host)s/%(dbname)s?charset=utf8' %{
    'user': MYSQL_USER,
    'pass': MYSQL_PASS,
    'host': MYSQL_HOST,
    'dbname': MYSQL_DBNAME,
    }
engine = create_engine(DB_CONNECT_STRING, echo=True)
DB_Session = sessionmaker(bind=engine)
session = DB_Session()
from sqlalchemy import Column, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
class Task(Base):
    __tablename__ = '%stask' % MYSQL_TABLE_PRE

    id = Column(Integer, primary_key=True)
    uid = Column(Integer, index=True)
    status = Column(Integer, index=True)
    param1 = Column(String(4096))
    param2 = Column(String(200))
    param3 = Column(String(200))
    misc = Column(Text)
    add_time = Column(Integer)
    start_time = Column(Integer)
    end_time = Column(Integer)
    ret = Column(Integer, index=True)
    retmsg = Column(String(200))
    client_name = Column(String(200))

    def __repr__(self):
        return
        '''<Task(id'%s',client_name'%s',status'%s',ret'%s',retmsg'%s')>''' %(self.id, self.client_name, \
            self.status, self.ret, self.retmsg)

class User(Base):
    __tablename__ = '%suser' % MYSQL_TABLE_PRE

    id = Column(Integer, primary_key=True)
    openid = Column(String(200), index=True)
    nickname = Column(String(200))
    sex = Column(Integer)
    groupid = Column(Integer)
    add_time = Column(Integer)
    misc = Column(Text)

    def __repr__(self):
        return '''<User('%s','%s','%s','%s')>''' % (self.openid, \
           self.nickname, self.sex, self.groupid)

class Option(Base):
    __tablename__ = '%soptions' % MYSQL_TABLE_PRE

    id = Column(Integer, primary_key=True)
    name = Column(String(200))
    value = Column(String(200))

def init_db():
    Base.metadata.create_all(engine)

def drop_db():
    Base.metadata.drop_all(engine)

