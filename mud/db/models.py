"""Typed SQLAlchemy ORM models used throughout the persistence layer."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Declarative base with typing support for SQLAlchemy models."""

    # NOTE: PlayerAccount was removed as part of ROM character-login restoration.
    # Characters now own their password hash directly, mirroring ROM src/merc.h PCData.pwd.


class Area(Base):
    __tablename__ = "areas"

    id: Mapped[int] = mapped_column(primary_key=True)
    vnum: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String)
    min_vnum: Mapped[int] = mapped_column(Integer)
    max_vnum: Mapped[int] = mapped_column(Integer)
    rooms: Mapped[list["Room"]] = relationship("Room", back_populates="area")


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    vnum: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(String)
    sector_type: Mapped[int] = mapped_column(Integer)
    room_flags: Mapped[int] = mapped_column(Integer)
    area_id: Mapped[int | None] = mapped_column(ForeignKey("areas.id"), nullable=True)
    area: Mapped[Area | None] = relationship("Area", back_populates="rooms")
    exits: Mapped[list["Exit"]] = relationship("Exit", back_populates="room")


class Exit(Base):
    __tablename__ = "exits"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    direction: Mapped[str] = mapped_column(String)
    to_room_vnum: Mapped[int] = mapped_column(Integer)
    room: Mapped[Room | None] = relationship("Room", back_populates="exits")


class MobPrototype(Base):
    __tablename__ = "mob_prototypes"

    id: Mapped[int] = mapped_column(primary_key=True)
    vnum: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String)
    short_desc: Mapped[str] = mapped_column(String)
    long_desc: Mapped[str] = mapped_column(String)
    level: Mapped[int] = mapped_column(Integer)
    alignment: Mapped[int] = mapped_column(Integer)


class ObjPrototype(Base):
    __tablename__ = "obj_prototypes"

    id: Mapped[int] = mapped_column(primary_key=True)
    vnum: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String)
    short_desc: Mapped[str] = mapped_column(String)
    long_desc: Mapped[str] = mapped_column(String)
    item_type: Mapped[int] = mapped_column(Integer)
    flags: Mapped[int] = mapped_column(Integer)
    value0: Mapped[int] = mapped_column(Integer)
    value1: Mapped[int] = mapped_column(Integer)
    value2: Mapped[int] = mapped_column(Integer)
    value3: Mapped[int] = mapped_column(Integer)


class ObjectInstance(Base):
    __tablename__ = "object_instances"

    id: Mapped[int] = mapped_column(primary_key=True)
    prototype_vnum: Mapped[int] = mapped_column(Integer, ForeignKey("obj_prototypes.vnum"))
    location: Mapped[str] = mapped_column(String)
    character_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("characters.id"), nullable=True)

    prototype: Mapped[ObjPrototype | None] = relationship("ObjPrototype")
    character: Mapped["Character | None"] = relationship("Character", back_populates="objects")


class Character(Base):
    """ROM-faithful character record.

    Password is stored directly on the character row, mirroring ROM
    src/merc.h PCData.pwd and the save.c pfile format.  The Python-only
    PlayerAccount table has been removed.
    """

    __tablename__ = "characters"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    password_hash: Mapped[str] = mapped_column(String, default="")
    level: Mapped[int] = mapped_column(Integer)
    hp: Mapped[int] = mapped_column(Integer)
    room_vnum: Mapped[int] = mapped_column(Integer)
    race: Mapped[int] = mapped_column(Integer, default=0)
    ch_class: Mapped[int] = mapped_column(Integer, default=0)
    sex: Mapped[int] = mapped_column(Integer, default=0)
    true_sex: Mapped[int] = mapped_column(Integer, default=0)
    alignment: Mapped[int] = mapped_column(Integer, default=0)
    act: Mapped[int] = mapped_column(Integer, default=0)
    hometown_vnum: Mapped[int] = mapped_column(Integer, default=0)
    perm_stats: Mapped[str] = mapped_column(String, default="")
    size: Mapped[int] = mapped_column(Integer, default=0)
    form: Mapped[int] = mapped_column(Integer, default=0)
    parts: Mapped[int] = mapped_column(Integer, default=0)
    imm_flags: Mapped[int] = mapped_column(Integer, default=0)
    res_flags: Mapped[int] = mapped_column(Integer, default=0)
    vuln_flags: Mapped[int] = mapped_column(Integer, default=0)
    practice: Mapped[int] = mapped_column(Integer, default=0)
    train: Mapped[int] = mapped_column(Integer, default=0)
    perm_hit: Mapped[int] = mapped_column(Integer, default=20)
    perm_mana: Mapped[int] = mapped_column(Integer, default=100)
    perm_move: Mapped[int] = mapped_column(Integer, default=100)
    default_weapon_vnum: Mapped[int] = mapped_column(Integer, default=0)
    newbie_help_seen: Mapped[bool] = mapped_column(Boolean, default=False)
    creation_points: Mapped[int] = mapped_column(Integer, default=40)
    creation_groups: Mapped[str] = mapped_column(String, default="")
    creation_skills: Mapped[str] = mapped_column(String, default="")

    # --- INV-008 Phase 1: new columns for DB-canonical persistence ---
    # Scalar fields missing from original schema
    max_hit: Mapped[int] = mapped_column(Integer, default=20)
    mana: Mapped[int] = mapped_column(Integer, default=100)
    move: Mapped[int] = mapped_column(Integer, default=100)
    gold: Mapped[int] = mapped_column(Integer, default=0)
    silver: Mapped[int] = mapped_column(Integer, default=0)
    exp: Mapped[int] = mapped_column(Integer, default=0)
    trust: Mapped[int] = mapped_column(Integer, default=0)
    invis_level: Mapped[int] = mapped_column(Integer, default=0)
    incog_level: Mapped[int] = mapped_column(Integer, default=0)
    saving_throw: Mapped[int] = mapped_column(Integer, default=0)
    hitroll: Mapped[int] = mapped_column(Integer, default=0)
    damroll: Mapped[int] = mapped_column(Integer, default=0)
    wimpy: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[int] = mapped_column(Integer, default=8)  # Position.STANDING = 8
    played: Mapped[int] = mapped_column(Integer, default=0)
    logon: Mapped[int] = mapped_column(Integer, default=0)
    lines: Mapped[int] = mapped_column(Integer, default=22)
    prompt: Mapped[str | None] = mapped_column(String, nullable=True)
    prefix: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str | None] = mapped_column(String, nullable=True)
    bamfin: Mapped[str | None] = mapped_column(String, nullable=True)
    bamfout: Mapped[str | None] = mapped_column(String, nullable=True)
    security: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    last_level: Mapped[int] = mapped_column(Integer, default=0)
    affected_by: Mapped[int] = mapped_column(Integer, default=0)
    comm: Mapped[int] = mapped_column(Integer, default=0)
    wiznet: Mapped[int] = mapped_column(Integer, default=0)
    log_commands: Mapped[bool] = mapped_column(Boolean, default=False)
    pfile_version: Mapped[int] = mapped_column(Integer, default=1)  # TABLES-001
    board: Mapped[str] = mapped_column(String, default="general")
    # JSON collection fields
    mod_stat: Mapped[list | None] = mapped_column(JSON, nullable=True)
    armor: Mapped[list | None] = mapped_column(JSON, nullable=True)
    conditions: Mapped[list | None] = mapped_column(JSON, nullable=True)
    aliases: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    skills: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    groups: Mapped[list | None] = mapped_column(JSON, nullable=True)
    last_notes: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    colours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    pet_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # Option A from audit §3.1: full inventory/equipment as JSON blobs
    inventory_state: Mapped[list | None] = mapped_column(JSON, nullable=True)
    equipment_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    objects: Mapped[list[ObjectInstance]] = relationship("ObjectInstance", back_populates="character")
