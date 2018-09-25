# -*- coding: utf-8 -*-
from . import db, VehicleDescription
from APITaxi_utils.mixins import (AsDictMixin, HistoryMixin, unique_constructor,
        MarshalMixin, FilterOr404Mixin)
from APITaxi_utils import fields
from sqlalchemy_defaults import Column
from flask_login import current_user
from flask_restplus import abort

@unique_constructor(db.session,
                    lambda licence_plate, *args, **kwargs: licence_plate,
                    lambda query, licence_plate, *args, **kwargs: query.filter(Vehicle.licence_plate == licence_plate))
class Vehicle(db.Model, AsDictMixin, MarshalMixin, FilterOr404Mixin):
    id = Column(db.Integer, primary_key=True)
    licence_plate = Column(db.String(80), label='Immatriculation',
            description='Immatriculation du véhicule',
            unique=True)
    descriptions = db.relationship("VehicleDescription",
            lazy='joined')

    def __init__(self, *args, **kwargs):
        from . import Taxi, RawTaxi
        db.Model.__init__(self, licence_plate=kwargs['licence_plate'])
        db.session.add(self)
        db.session.commit()
        del kwargs['licence_plate']
        desc = VehicleDescription(vehicle_id=self.id, status='off', **kwargs)
        db.session.add(desc)
        for taxi in Taxi.query.filter_by(vehicle_id=self.id).all():
            RawTaxi.flush(taxi.id)
        db.session.commit()

    @classmethod
    def add_description(cls, add_description, dict_description):
        if not add_description:
            return
        for k, v in list(dict_description.items()):
            dict_description[k].attribute = 'description.{}'.format(k)


    @classmethod
    def marshall_obj(cls, show_all=False, filter_id=False, level=0, api=None,
                    add_description=True):
        if level >=2:
            return {}
        return_ = super(Vehicle, cls).marshall_obj(show_all, filter_id,
                level=level+1, api=api)
        dict_description = VehicleDescription.marshall_obj(
                show_all, filter_id, level=level+1, api=api)
        dict_description.update({"model": fields.String(attribute="model"),
                        "constructor": fields.String(attribute="constructor")})
        cls.add_description(add_description, dict_description)
        return_.update(dict_description)
        if not filter_id:
            return_["id"] = fields.Integer()
        if "internal_id" in list(return_.keys()):
            del return_["internal_id"]
        return return_

    @property
    def description(self):
        return self.get_description()

    def get_description(self, user=None):
        if not user:
            user = current_user
        if user.is_anonymous:
            return None
        for description in self.descriptions:
            if description.added_by == user.id:
                return description
        return None


    def is_vehicle_description_attribute(self, attrname):
        return attrname in VehicleDescription.__table__.columns or\
           attrname in VehicleDescription._additionnal_keys and\
           attrname not in self.__table__.columns


    def __getattr__(self, attrname):
        if self.is_vehicle_description_attribute(attrname):
            description = self.description
            try:
                return db.Model.__getattribute__(description, attrname)
            except AttributeError as e:
                pass
        return db.Model.__getattribute__(self, attrname)

    def get_or_create_desription(self):
        description = self.description
        if not description:
            description = VehicleDescription(vehicle_id=self.id, status='off')
        return description

    def __setattr__(self, attrname, value):
        if self.is_vehicle_description_attribute(attrname):
            description = self.get_or_create_desription()
            try:
                r = db.Model.__setattr__(description, attrname, value)
            except AttributeError as e:
                pass
            db.session.add(description)
            return r
        return db.Model.__setattr__(self, attrname, value)


    @classmethod
    def filter_by_or_404(cls, licence_plate):
        r = super(Vehicle, cls).filter_by_or_404(licence_plate=licence_plate)
        if r.description is None:
            abort(404, message="This vehicle was not added by this user")
        return r

    def __repr__(self):
        return '<Vehicle %r>' % str(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

    @classmethod
    def to_exclude(cls):
        columns = list([f for f in list(HistoryMixin.__dict__.keys()) if isinstance(getattr(HistoryMixin, f), Column)])
        columns += ["Vehicle", "vehicle_taxi", "descriptions"]
        return columns
