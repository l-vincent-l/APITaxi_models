# -*- coding: utf-8 -*-
from . import db, VehicleDescription
from APITaxi_utils.mixins import (AsDictMixin, HistoryMixin, unique_constructor,
        MarshalMixin, FilterOr404Mixin)
from APITaxi_utils import fields
from APITaxi_utils.caching import CacheableMixin, query_callable
from sqlalchemy_defaults import Column
from flask_login import current_user
from flask_restplus import abort

@unique_constructor(db.session,
                    lambda licence_plate, *args, **kwargs: licence_plate,
                    lambda query, licence_plate, *args, **kwargs: query.filter(Vehicle.licence_plate == licence_plate))
class Vehicle(CacheableMixin, db.Model, AsDictMixin, MarshalMixin, FilterOr404Mixin):
    cache_label = 'taxis'
    query_class = query_callable()
    id = Column(db.Integer, primary_key=True)
    licence_plate = Column(db.String(80), label=u'Immatriculation',
            description=u'Immatriculation du véhicule',
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
        if add_description:
            for k, v in dict_description.items():
                dict_description[k].attribute = 'description.{}'.format(k)
        return_.update(dict_description)
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
        if user.is_anonymous:
            return None
        for description in self.descriptions:
            if description.added_by == user.id:
                return description
        return None


    def __getattr__(self, attrname):
        if attrname in VehicleDescription.__table__.columns or\
           attrname in VehicleDescription._additionnal_keys and\
           attrname not in self.__table__.columns:
            description = self.description
            try:
                return getattr(description, attrname)
            except AttributeError as e:
                pass
        return db.Model.__getattribute__(self, attrname)


    @classmethod
    def filter_by_or_404(cls, licence_plate):
        r = super(Vehicle, cls).filter_by_or_404(licence_plate=licence_plate)
        if r.description is None:
            abort(404, message="This vehicle was not added by this user")
        return r

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
