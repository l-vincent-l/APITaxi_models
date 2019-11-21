# -*- coding: utf-8 -*-
from . import db, Driver, ZUPC, Vehicle
from APITaxi_utils.mixins import AsDictMixin, HistoryMixin, FilterOr404Mixin
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy_defaults import Column
from sqlalchemy.types import Enum
from sqlalchemy import Index
from APITaxi_utils import fields

owner_type_enum = ['company', 'individual']
class ADS(db.Model, HistoryMixin, AsDictMixin, FilterOr404Mixin):

    def get_zupc_id(self, **kwargs):
        zupc = ZUPC.query.filter_by(insee=kwargs['insee']).first()
        if zupc is None:
            raise KeyError("Unable to find a ZUPC for insee: {}".format(kwargs['insee']))
        return zupc.parent_id


    def __init__(self, *args, **kwargs):
        if "vehicle_id" not in kwargs or kwargs.get("vehicle_id") == 0:
            kwargs["vehicle_id"] = None
        if kwargs["vehicle_id"] and not Vehicle.query.get(kwargs["vehicle_id"]):
            raise KeyError("Unable to find a vehicle with the id: {}".format(
                kwargs["vehicle_id"]))
        kwargs['zupc_id'] = self.get_zupc_id(**kwargs)
        db.Model.__init__(self, *args, **kwargs)
        HistoryMixin.__init__(self)
        current_ads = ADS.query.filter_by(
                numero=self.numero,
                insee=self.insee
            ).order_by(
                ADS.id.desc()
            ).first()
        if current_ads:
            self.id = current_ads.id
            db.session.merge(self)
        else:
            db.session.add(self)
        db.session.commit()

    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))

    public_fields = set(['numero', 'insee'])
    id = Column(db.Integer, primary_key=True)
    numero = Column(db.String, label='Numéro',
            description='Numéro de l\'ADS')
    doublage = Column(db.Boolean, label='Doublage', default=False,
            nullable=True, description='L\'ADS est elle doublée ?')
    insee = Column(db.String, label='Code INSEE de la commune d\'attribution',
                   description='Code INSEE de la commune d\'attribution')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    owner_type = Column(Enum(*owner_type_enum, name='owner_type_enum'),
            label='Type Propriétaire')
    owner_name = Column(db.String, label='Nom du propriétaire')
    category = Column(db.String, label='Catégorie de l\'ADS')
    zupc_id = db.Column(db.Integer, db.ForeignKey('ZUPC.id'), nullable=True)

    @property
    def zupc(self):
        return ZUPC.query.get(self.zupc_id)

    @classmethod
    def marshall_obj(cls, show_all=False, filter_id=False, level=0, api=None):
        if level >=2:
            return {}
        return_ = super(ADS, cls).marshall_obj(show_all, filter_id,
                level=level+1, api=api)
        return_['vehicle_id'] = fields.Integer(column=cls.__table__.columns['vehicle_id'])
        return return_

    @property
    def vehicle(self):
        return vehicle.Vehicle.query.get(self.vehicle_id)

    @vehicle.setter
    def vehicle(self, vehicle):
        if isinstance(vehicle, string_types):
            self.__vehicle = Vehicle(vehicle)
        else:
            self.__vehicle = Vehicle(vehicle.licence_plate)


    def __repr__(self):
        return '<ADS %r>' % str(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)


ads_numero_index = Index('ads_numero_index', ADS.numero)
ads_insee_index = Index('ads_insee_index', ADS.insee)