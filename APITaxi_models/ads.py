# -*- coding: utf-8 -*-
from . import db, Driver, ZUPC, Vehicle
from APITaxi_utils.mixins import AsDictMixin, HistoryMixin, FilterOr404Mixin
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy_defaults import Column
from sqlalchemy.types import Enum
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
        db.session.add(self)
        db.session.commit()
        cur = db.session.connection().connection.cursor()
        cur.execute(""" UPDATE taxi set ads_id = %s WHERE ads_id IN (
                                SELECT id FROM "ADS"  WHERE numero = %s
                                AND insee = %s)
                        """, (self.id, self.numero, self.insee)
        )
        db.session.commit()

    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))

    public_fields = set(['numero', 'insee'])
    id = Column(db.Integer, primary_key=True)
    numero = Column(db.String, label=u'Numéro',
            description=u'Numéro de l\'ADS')
    doublage = Column(db.Boolean, label=u'Doublage', default=False,
            nullable=True, description=u'L\'ADS est elle doublée ?')
    insee = Column(db.String, label=u'Code INSEE de la commune d\'attribution',
                   description=u'Code INSEE de la commune d\'attribution')
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'), nullable=True)
    owner_type = Column(Enum(*owner_type_enum, name='owner_type_enum'),
            label=u'Type Propriétaire')
    owner_name = Column(db.String, label=u'Nom du propriétaire')
    category = Column(db.String, label=u'Catégorie de l\'ADS')
    zupc_id = db.Column(db.Integer, db.ForeignKey('ZUPC.id'), nullable=True)

    @property
    def zupc(self):
        return ZUPC.cache.get(self.zupc_id)

    @classmethod
    def can_be_listed_by(cls, user):
        return super(ADS, cls).can_be_listed_by(user) or user.has_role('prefecture')

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
        return '<ADS %r>' % unicode(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)
