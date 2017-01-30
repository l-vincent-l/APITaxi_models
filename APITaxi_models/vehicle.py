# -*- coding: utf-8 -*-
from . import db, VehicleDescription
from APITaxi_utils.mixins import (AsDictMixin, HistoryMixin, unique_constructor,
        MarshalMixin, FilterOr404Mixin)
from APITaxi_utils import fields
from APITaxi_utils.caching import CacheableMixin, query_callable
from sqlalchemy_defaults import Column
from flask_login import current_user

@unique_constructor(db.session,
                    lambda licence_plate: licence_plate,
                    lambda query, licence_plate: query.filter(Vehicle.licence_plate == licence_plate))
class Vehicle(CacheableMixin, db.Model, AsDictMixin, MarshalMixin, FilterOr404Mixin):
    cache_label = 'taxis'
    query_class = query_callable()
    id = Column(db.Integer, primary_key=True)
    licence_plate = Column(db.String(80), label=u'Immatriculation',
            description=u'Immatriculation du véhicule',
            unique=True)
    descriptions = db.relationship("VehicleDescription",
            lazy='joined')

    def __init__(self, licence_plate=None):
        if isinstance(licence_plate, self.__class__):
            self.licence_plate = licence_plate.licence_plate
        else:
            self.licence_plate

    @classmethod
    def marshall_obj(cls, show_all=False, filter_id=False, level=0, api=None):
        if level >=2:
            return {}
        return_ = super(Vehicle, cls).marshall_obj(show_all, filter_id,
                level=level+1, api=api)
        dict_description = VehicleDescription.marshall_obj(
                show_all, filter_id, level=level+1, api=api)
        for k, v in dict_description.items():
            dict_description[k].attribute = 'description.{}'.format(k)
        return_.update(dict_description)
        return_.update({"model": fields.String(attribute="description.model"),
                        "constructor": fields.String(attribute="description.constructor")})
        if not filter_id:
            return_["id"] = fields.Integer()
        if "internal_id" in return_.keys():
            del return_["internal_id"]
        return return_


    @property
    def description(self):
        return self.get_description()


    def get_description(self, user=None):
        if not user:
            user = current_user
        returned_description = None
        for description in self.descriptions:
            if description.added_by == user.id:
                returned_description = description
        return returned_description


    @property
    def model(self):
        return self.description.model if self.description else None


    @property
    def constructor(self):
        return self.description.constructor.name if self.description else None

    @property
    def model_year(self):
        return self.description.model_year if self.description else None

    @property
    def engine(self):
        return self.description.engine if self.description else None

    @property
    def horse_power(self):
        return self.description.horse_power if self.description else None

    @property
    def relais(self):
        return self.description.relais if self.description else None

    @property
    def horodateur(self):
        return self.description.horodateur if self.description else None

    @property
    def taximetre(self):
        return self.description.taximetre if self.description else None

    @property
    def date_dernier_ct(self):
        return self.description.date_dernier_ct if self.description else None

    @property
    def date_validite_ct(self):
        return self.description.date_validite_ct if self.description else None

    @property
    def type_(self):
        return self.description.type_ if self.description else None

    @property
    def internal_id(self):
        return self.description.internal_id if self.description else None

    def __repr__(self):
        return '<Vehicle %r>' % unicode(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def to_exclude(cls):
        columns = list(filter(lambda f: isinstance(getattr(HistoryMixin, f), Column), HistoryMixin.__dict__.keys()))
        columns += ["Vehicle", "vehicle_taxi", "descriptions"]
        return columns
