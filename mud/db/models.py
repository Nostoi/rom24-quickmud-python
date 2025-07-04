from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Area(Base):
    __tablename__ = "areas"
    id = Column(Integer, primary_key=True)
    vnum = Column(Integer, unique=True)
    name = Column(String)
    min_vnum = Column(Integer)
    max_vnum = Column(Integer)
    rooms = relationship("Room", back_populates="area")

class Room(Base):
    __tablename__ = "rooms"
    id = Column(Integer, primary_key=True)
    vnum = Column(Integer, unique=True)
    name = Column(String)
    description = Column(String)
    sector_type = Column(Integer)
    room_flags = Column(Integer)
    area_id = Column(Integer, ForeignKey("areas.id"))
    area = relationship("Area", back_populates="rooms")
    exits = relationship("Exit", back_populates="room")

class Exit(Base):
    __tablename__ = "exits"
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey("rooms.id"))
    direction = Column(String)
    to_room_vnum = Column(Integer)
    room = relationship("Room", back_populates="exits")

class MobPrototype(Base):
    __tablename__ = "mob_prototypes"
    id = Column(Integer, primary_key=True)
    vnum = Column(Integer, unique=True)
    name = Column(String)
    short_desc = Column(String)
    long_desc = Column(String)
    level = Column(Integer)
    alignment = Column(Integer)

class ObjPrototype(Base):
    __tablename__ = "obj_prototypes"
    id = Column(Integer, primary_key=True)
    vnum = Column(Integer, unique=True)
    name = Column(String)
    short_desc = Column(String)
    long_desc = Column(String)
    item_type = Column(Integer)
    flags = Column(Integer)
    value0 = Column(Integer)
    value1 = Column(Integer)
    value2 = Column(Integer)
    value3 = Column(Integer)


class PlayerAccount(Base):
    __tablename__ = "player_accounts"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    password_hash = Column(String)

    characters = relationship("Character", back_populates="player")


class Character(Base):
    __tablename__ = "characters"
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    level = Column(Integer)
    hp = Column(Integer)
    room_vnum = Column(Integer)

    player_id = Column(Integer, ForeignKey("player_accounts.id"))
    player = relationship("PlayerAccount", back_populates="characters")

