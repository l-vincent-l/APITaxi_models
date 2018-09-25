# -*- coding: utf-8 -*-
from flask_security import UserMixin, RoleMixin
from flask_security.utils import encrypt_password
from APITaxi_utils.mixins import MarshalMixin, FilterOr404Mixin
from . import db
from sqlalchemy_defaults import Column
from sqlalchemy.dialects.postgresql import UUID
import uuid

roles_users = db.Table('roles_users',
        db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))

class Role(db.Model, RoleMixin, MarshalMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class UserBase(object):

    def hail_endpoint(self, env):
        if env == 'PROD':
            return self.hail_endpoint_production
        elif env == 'STAGING':
            return self.hail_endpoint_staging
        elif env == 'DEV':
            return self.hail_endpoint_testing
        return None

class User(db.Model, UserMixin, MarshalMixin, FilterOr404Mixin,
        UserBase):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255))
    active = db.Column(db.Boolean())
    confirmed_at = db.Column(db.DateTime())
    roles = db.relationship('Role', secondary=roles_users,
                            lazy='joined')
    apikey = db.Column(db.String(36), nullable=False)
    hail_endpoint_production = Column(db.String, nullable=True,
            label='Hail endpoint production',
            description='Hail endpoint production')
    hail_endpoint_staging = Column(db.String, nullable=True,
            label='Hail endpoint staging',
            description='Hail endpoint staging')
    hail_endpoint_testing = Column(db.String, nullable=True,
            label='Hail endpoint testing',
            description='Hail endpoint testing')
    commercial_name = Column(db.String, nullable=True, label='Nom commercial',
            description='Votre nom commercial')
    phone_number_customer = Column(db.String, nullable=True,
            label='Numéro de téléphone du service client',
            description='Numéro de téléphone de support pour les clients')
    phone_number_technical = Column(db.String, nullable=True,
            label='Numéro de téléphone du contact technique',
            description='Numéro de téléphone du contact technique')
    email_customer = Column(db.String, nullable=True,
            label='Email du service client',
            description='Email de support pour les clients')
    email_technical = Column(db.String, nullable=True,
            label='Email du contact technique',
            description='Email du contact technique')
    logos = db.relationship('Logo', backref="user", lazy='joined')
    operator_header_name = Column(db.String, nullable=True,
            label='Nom du header http pour l\'authentification',
            description="""Cet header sera envoyé lors de la communication
                de l'ODT vers votre serveur""")
    operator_api_key = Column(db.String, nullable=True,
            label='Valeur de la clé d\'api',
            description="""Valeur de la clé d'api envoyé par l'ODT
            à votre serveur pour l'authentification.""")

    def __init__(self, *args, **kwargs):
        kwargs['apikey'] = str(uuid.uuid4())
        kwargs['password'] = encrypt_password(kwargs['password'])
        kwargs['active'] = True
        super(self.__class__, self).__init__(*args, **kwargs)


class Logo(db.Model):
    id = db.Column(UUID, primary_key=True)
    size=db.Column(db.String)
    format_=db.Column(db.String)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
