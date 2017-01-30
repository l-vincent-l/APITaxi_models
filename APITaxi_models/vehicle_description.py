# -*- coding: utf-8 -*-
from . import db, Constructor, Model
from .security import User
from sqlalchemy_defaults import Column
from APITaxi_utils.caching import CacheableMixin, query_callable
from APITaxi_utils.mixins import unique_constructor, HistoryMixin, AsDictMixin
from sqlalchemy.types import Enum
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy import UniqueConstraint, and_
from flask import current_app
from time import time
from itertools import compress

status_vehicle_description_enum = ['free', 'answering', 'occupied', 'oncoming', 'off']
@unique_constructor(db.session,
           lambda vehicle_id, added_by, **kw: '{}, {}'.format(vehicle_id, added_by),
           lambda query, vehicle_id, added_by, **kw:\
                   query.filter(and_(\
                       VehicleDescription.vehicle_id == vehicle_id,
                       VehicleDescription.added_by == added_by)))
class VehicleDescription(HistoryMixin, CacheableMixin, db.Model, AsDictMixin):
    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))
    cache_label = 'taxis'
    query_class = query_callable()
    _additionnal_keys = ['constructor', 'model']

    def __init__(self, **kwargs):
        db.Model.__init__(self, **kwargs)
        HistoryMixin.__init__(self)

    id = Column(db.Integer, primary_key=True)
    model_id = Column(db.Integer, db.ForeignKey("model.id"))
    __model = db.relationship('Model', lazy='joined')
    constructor_id = Column(db.Integer, db.ForeignKey("constructor.id"))
    __constructor = db.relationship('Constructor', lazy='joined')
    model_year = Column(db.Integer, label=u'Année', nullable=True,
            description=u'Année de mise en production du véhicule')
    engine = Column(db.String(80), label=u'Motorisation', nullable=True,
            description=u'Motorisation du véhicule, champ P3')
    horse_power = Column(db.Float(), label=u'Puissance', nullable=True,
            description=u'Puissance du véhicule en chevaux fiscaux')
    relais = Column(db.Boolean, label=u'Relais', default=False, nullable=True,
            description=u'Est-ce un véhicule relais')
    horodateur = Column(db.String(255), label=u'Horodateur', nullable=True,
            description=u'Modèle de l\'horodateur')
    taximetre = Column(db.String(255), label=u'Taximètre', nullable=True,
            description=u'Modèle du taximètre')
    date_dernier_ct = Column(db.Date(),
        label=u'Date du dernier CT (format année-mois-jour)',
        description=u'Date du dernier contrôle technique')
    date_validite_ct = Column(db.Date(),
        label=u'Date de la fin de validité du CT (format année-mois-jour)',
        description=u'Date de fin de validité du contrôle technique')
    special_need_vehicle = Column(db.Boolean, name='special_need_vehicle',
            label=u'Véhicule spécialement aménagé pour PMR ', nullable=True)
    type_ = Column(Enum('sedan', 'mpv', 'station_wagon', 'normal', name='vehicle_type_enum'),
            label='Type', nullable=True)
    luxury = Column(db.Boolean, name='luxury', label='Luxe ?', nullable=True)
    credit_card_accepted = Column(db.Boolean, name='credit_card_accepted',
            label=u'Carte bancaire acceptée ?', nullable=True)
    nfc_cc_accepted = Column(db.Boolean, name='nfc_cc_accepted',
            label=u'Paiement sans contact sur carte bancaire accepté ?',
            nullable=True)
    amex_accepted = Column(db.Boolean, name='amex_accepted',
            label=u'AMEX acceptée ?', nullable=True)
    bank_check_accepted = Column(db.Boolean, name='bank_check_accepted',
            label=u'Chèque bancaire accepté ?', nullable=True)
    fresh_drink = Column(db.Boolean, name='fresh_drink',
            label=u'Boisson fraiche ?', nullable=True)
    dvd_player = Column(db.Boolean, name='dvd_player', label='Lecteur DVD ?',
            nullable=True)
    tablet = Column(db.Boolean, name='tablet', label='Tablette ?',
            nullable=True)
    wifi = Column(db.Boolean, name='wifi', label=u'Wifi à bord ?',
            nullable=True)
    baby_seat = Column(db.Boolean, name='baby_seat', label=u'Siège bébé ?',
            nullable=True)
    bike_accepted = Column(db.Boolean, name='bike_accepted',
            label=u'Transport de vélo', nullable=True)
    pet_accepted = Column(db.Boolean, name='pet_accepted',
            label=u'Animaux de compagnie acceptés ?', nullable=True)
    air_con = Column(db.Boolean, name='air_con',
            label=u'Véhicule climatisé', nullable=True)
    electronic_toll = Column(db.Boolean, name='electronic_toll',
            label=u'Véhicule équipé du télépéage', nullable=True)
    gps = Column(db.Boolean, name='gps', label=u'Véhicule équipé d\'un GPS',
            nullable=True)
    cpam_conventionne = Column(db.Boolean, name='cpam_conventionne',
            label=u'Conventionné assurance maladie', nullable=True)
    every_destination = Column(db.Boolean, name='every_destination',
            label=u'Toute destination', nullable=True)
    color = Column(db.String(255), name='color', label='Couleur : ',
            nullable=True)
    vehicle_id = Column(db.Integer, db.ForeignKey('vehicle.id'))
    UniqueConstraint('vehicle_id', 'added_by', name="uq_vehicle_description")
    _status = Column(Enum(*status_vehicle_description_enum,
        name='status_taxi_enum'), nullable=True, default='free', name='status')
    nb_seats = Column(db.Integer, name='nb_seats',
            description=u'Nombre de places assises disponibles pour les voyageurs',
            label=u'Nombre de places')
    internal_id = Column(db.String, nullable=True)
    __table_args__ = (db.UniqueConstraint('vehicle_id', 'added_by',
        name="_uq_vehicle_description"),)

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        assert value is None or value == 'None' or value in status_vehicle_description_enum,\
                '{} is not a valid status, (valid statuses are {})'\
                    .format(value, status_vehicle_description_enum)
        self._status = value
        from .taxis import Taxi
        operator = User.query.get(self.added_by)
        for t in Taxi.query.join(Taxi.vehicle, aliased=True).filter_by(id=self.vehicle_id):
            t.set_avaibility(operator.email, self._status)
            current_app.extensions['redis_saved'].zadd(
                'taxi_status:{}'.format(t.id),
                float(time()),
                '{}_{}'.format(self._status, time()),
            )


    @classmethod
    def to_exclude(cls):
        return list(HistoryMixin.to_exclude()) + ['status']

    @property
    def constructor(self):
        return self.__constructor.name

    @constructor.setter
    def constructor(self, name):
        self.__constructor = Constructor(name)

    @property
    def model(self):
        return self.__model.name

    @model.setter
    def model(self, name):
        self.__model = Model(name)

    @property
    def characteristics(self):
        return VehicleDescription.get_characs(lambda o, f: getattr(o, f), self)

    @staticmethod
    def get_characs(getattr_, obj):
        fields = ['special_need_vehicle', 'every_destination', 'gps',
            'electronic_toll', 'air_con', 'pet_accepted', 'bike_accepted',
            'baby_seat', 'wifi', 'tablet', 'dvd_player', 'fresh_drink',
            'amex_accepted', 'bank_check_accepted', 'nfc_cc_accepted',
            'credit_card_accepted', 'luxury']
        return list(compress(fields, map(lambda f: getattr_(obj, f), fields)))


