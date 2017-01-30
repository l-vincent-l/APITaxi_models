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
            self.licence_plate = licence_plate

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

    def __getattr__(self, attrname):
        try:
            return db.Model.__getattribute__(self, attrname)
        except AttributeError as e:
            description = self.description
            if description is None:
                return None
            if attrname in VehicleDescription.__table__.columns:
                try:
                    return db.Model.__getattribute__(description, attrname)
                except AttributeError:
                    pass
            raise e

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
