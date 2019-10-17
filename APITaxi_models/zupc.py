# -*- coding: utf-8 -*-
from . import db
from sqlalchemy_defaults import Column
from APITaxi_utils.mixins import MarshalMixin, FilterOr404Mixin
from geoalchemy2 import Geography
from geoalchemy2.shape import to_shape
from shapely.prepared import prep
from sqlalchemy import func, Index
from datetime import datetime
from flask import current_app


class ZUPC(db.Model, MarshalMixin):
    id = Column(db.Integer, primary_key=True)
    departement_id = Column(db.Integer, db.ForeignKey('departement.id'))
    nom = Column(db.String(255), label='Nom')
    insee = Column(db.String(), nullable=True)
    shape = Column(Geography(geometry_type='MULTIPOLYGON', srid=4326,
        spatial_index=False), label='Geography of the shape')
    departement = db.relationship('Departement',
            backref=db.backref('departements'), lazy='joined')
    parent_id = Column(db.Integer, db.ForeignKey('ZUPC.id'))
    parent = db.relationship('ZUPC', remote_side=[id], lazy='joined')
    active = Column(db.Boolean, default=False)
    max_distance = Column(db.Integer, nullable=True, default=-1, label="Max distance in meters")
    __geom = None
    __preped_geom = None
    __bounds = None
    __table_args__ = (Index('zupc_shape_idx', 'shape'), Index('zupc_shape_igx', 'shape'))

    def __repr__(self):
        return '<ZUPC %r>' % str(self.id)

    def __str__(self):
        return self.nom

    @property
    def geom(self):
        if self.__geom is None:
            self.__geom = to_shape(self.shape)
        return self.__geom

    @property
    def preped_geom(self):
        if self.__preped_geom is None:
            self.__preped_geom = prep(self.geom)
        return self.__preped_geom

    @property
    def bounds(self):
        if not self.__bounds:
            self.__bounds = self.geom.bounds
        return self.__bounds

    @property
    def bottom(self):
        return self.bounds[1]

    @property
    def left(self):
        return self.bounds[0]

    @property
    def top(self):
        return self.bounds[3]

    @property
    def right(self):
        return self.bounds[2]

    def is_inactive(self):
        inactive_filter_period = current_app.config['INACTIVE_FILTER_PERIOD']
        hour = datetime.now().hour
        if inactive_filter_period[0] > inactive_filter_period[1]:
            return hour >= inactive_filter_period[0] or hour <= inactive_filter_period[1]
        else:
            return inactive_filter_period[0] <= hour <= inactive_filter_period[1]

    def get_max_distance(self, zupc_customer):
        #We can deactivate the max radius for a certain zone
        if self.is_inactive:
            return current_app.config['DEFAULT_MAX_RADIUS']
        else:
            return min([v for v in [v[2] for v in zupc_customer] if v and v>0]
                           + [current_app.config['DEFAULT_MAX_RADIUS']])
