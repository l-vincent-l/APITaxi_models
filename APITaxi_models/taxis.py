# -*- coding: utf-8 -*-
from . import (db, Departement, ADS, Driver, Vehicle,
               VehicleDescription, Model, Constructor)
from .security import User
from APITaxi_utils import fields, get_columns_names
from APITaxi_utils.mixins import (GetOr404Mixin, AsDictMixin, HistoryMixin,
    FilterOr404Mixin, unique_constructor)
from APITaxi_utils.caching import CacheableMixin, query_callable, cache_in
from APITaxi_utils.get_short_uuid import get_short_uuid
from sqlalchemy_defaults import Column
from sqlalchemy.types import Enum
from sqlalchemy.orm import validates
from six import string_types
from parse import with_pattern
import time
from flask import g, current_app
from sqlalchemy.ext.declarative import declared_attr
from datetime import datetime
from itertools import groupby, izip
from flask_login import current_user

@with_pattern(r'\d+(\.\d+)?')
def parse_number(str_):
    return int(float(str_))


class TaxiRedis(object):
    _caracs = None
    _DISPONIBILITY_DURATION = 2*60 #Used in "is_fresh, is_free'
    _FORMAT_OPERATOR = '{timestamp:Number} {lat} {lon} {status} {device}'
    _fresh_operateurs_timestamps = None


    def __init__(self, id_, caracs=None, caracs_list=None):
        self._caracs = caracs
        self.id = id_
        self._fresh_operateurs_timestamps = None
        if isinstance(caracs, dict):
            self._caracs = self.transform_caracs(caracs)
        if caracs_list:
            self._caracs = {v[0].split(':')[1]: {
                'coords': {'lat': v[1][1][0], 'lon': v[1][1][1]},
                'timestamp': v[1][2], 'distance': v[1][0]}
                    for v in caracs_list
            }
        if self._caracs:
            self._min_caracs = min(self._caracs.values(), key=lambda v: v['timestamp'])
        else:
            self._min_caracs = None

    @property
    def coords(self):
        return (self._min_caracs['coords'] if self._min_caracs else None)

    @property
    def distance(self):
        return (self._min_caracs['distance'] if self._min_caracs else None)

    @property
    def lon(self):
        return self.coords['lon'] if self._min_caracs else None

    @property
    def lat(self):
        return self.coords['lat'] if self._min_caracs else None

    @staticmethod
    def parse_redis(v):
        r = dict()
        r['timestamp'], r['lat'], r['lon'], r['status'], r['device'], r['version'] = v.decode().split(' ')
        r['timestamp'] = parse_number(r['timestamp'])
        return r

    def caracs(self, min_time):
        if self._caracs is None:
            self._caracs = self.__class__.retrieve_caracs(self.id)
        for i in self._caracs.iteritems():
            if i[1]['timestamp'] < min_time:
                continue
            yield i

    def is_fresh(self, operateur=None):
        min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        if operateur:
            v = current_app.extensions['redis'].hget('taxi:{}'.format(self.id), operateur)
            if not v:
                return False
            p = self.parse_redis(v)
            return p['timestamp'] > min_time
        else:
            try:
                self.caracs(min_time).next()
            except StopIteration:
                return False
            return True

    @staticmethod
    def transform_caracs(caracs):
        return {k.decode(): TaxiRedis.parse_redis(v) for k, v in caracs.iteritems()}

    @classmethod
    def retrieve_caracs(cls, id_):
        _, scan = current_app.extensions['redis'].hscan("taxi:{}".format(id_))
        if not scan:
            return []
        return cls.transform_caracs(scan)

    def set_min_time(self, min_time):
        return min_time or int(time.time() - self._DISPONIBILITY_DURATION)


    def get_operator(self, min_time=None, favorite_operator=None):
        min_time = self.set_min_time(min_time)
        possibilities = self.get_fresh_operateurs_timestamps(min_time)
        fav = filter(lambda v: v[0] == favorite_operator, possibilities)
        if fav:
            return fav[0]
        return max(possibilities, lambda v: v[1]) if possibilities else (None, None)


    def get_fresh_operateurs_timestamps(self, min_time=None):
        min_time = self.set_min_time(min_time)
        caracs = self.caracs(min_time)
        if not self._fresh_operateurs_timestamps:
            self._fresh_operateurs_timestamps = list(map(
                lambda email, c: (email, c['timestamp']),
                caracs
            ))
        return self._fresh_operateurs_timestamps


    def _is_free(self, descriptions, func_added_by, func_status, min_time=None):
        if not min_time:
            min_time = int(time.time() - self._DISPONIBILITY_DURATION)
        users = map(lambda u_c : u_c[0],
                    self.get_fresh_operateurs_timestamps(min_time))
        return len(users) > 0 and\
                all(map(lambda desc: func_added_by(desc) not in users\
                    or func_status(desc) == 'free',
                    descriptions))


    def set_avaibility(self, operator_email, status):
        taxi_id_operator = "{}:{}".format(self.id, operator_email)
        if status == 'free':
            current_app.extensions['redis'].zrem(
                current_app.config['REDIS_NOT_AVAILABLE'], taxi_id_operator)
        else:
            current_app.extensions['redis'].zadd(
                current_app.config['REDIS_NOT_AVAILABLE'], 0., taxi_id_operator)

def query_func(query, driver, vehicle, ads, **kwargs):
    departement = Departement.filter_by_or_404(numero=str(driver['departement']))
    driver = Driver.filter_by_or_404(
            professional_licence=driver['professional_licence'],
            departement_id=departement.id
    )
    vehicle = Vehicle.filter_by_or_404(licence_plate=vehicle['licence_plate'])
    ads = ADS.filter_by_or_404(numero=ads['numero'], insee=ads['insee'])
    if kwargs.get('id') and current_user.has_role('admin'):
        t = query.filter_by(id=kwargs['id'], driver_id=driver.id,
                            vehicle_id=vehicle.id, ads_id=ads.id)
        if not t:
            abort(404, message="Unable to find taxi")
        return t
    return query.filter_by(driver_id=driver.id, vehicle_id=vehicle.id, ads_id=ads.id)

@unique_constructor(db.session,
                   lambda driver, vehicle, ads, **kwargs:\
                    "{}:{}:{}:{}:{}".format(
                        driver, vehicle, ads, kwargs.get(id), current_user.id),
                    query_func)
class Taxi(CacheableMixin, db.Model, HistoryMixin, AsDictMixin, GetOr404Mixin,
        TaxiRedis):
    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))
    cache_label = 'taxis'
    query_class = query_callable()

    def __init__(self, *args, **kwargs):
        if kwargs.get('id') is None or not current_user.has_role('admin'):
            kwargs['id'] = str(get_short_uuid())
        status = kwargs.get('status', 'off')
        self.vehicle = Vehicle(internal_id=kwargs.get('internal_id'), **kwargs['vehicle'])
        departement = Departement.filter_by_or_404(numero=str(kwargs['driver']['departement']))
        self.driver = Driver.filter_by_or_404(
            departement_id=departement.id,
            professional_licence=kwargs['driver']['professional_licence']
        )
        self.ads = ADS.query.filter_by(**kwargs['ads']).first()
        db.Model.__init__(self, vehicle_id=self.vehicle_id,
                          driver_id=self.driver_id, ads_id=self.ads_id,
                         id=kwargs.get('id'))
        HistoryMixin.__init__(self)
        TaxiRedis.__init__(self, self.id)
        self.status = status
        db.session.add(self)

    id = Column(db.String, primary_key=True)
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'),
            nullable=True)
    vehicle = db.relationship('Vehicle', backref='vehicle_taxi', lazy='joined')
    ads_id = db.Column(db.Integer, db.ForeignKey('ADS.id'), nullable=True)
    ads = db.relationship('ADS', backref='ads', lazy='joined')
    driver_id = db.Column(db.Integer, db.ForeignKey('driver.id'),
            nullable=True)
    driver = db.relationship('Driver', backref='driver', lazy='joined')
    rating = db.Column(db.Float, default=4.5)
    current_hail_id = db.Column(db.String,
                    db.ForeignKey('hail.id', name='taxi_hail_id', use_alter=True),
                    nullable=True)
    current_hail = db.relationship('Hail', backref='hail', post_update=True,
                                  foreign_keys=[current_hail_id])

    _ACTIVITY_TIMEOUT = 15*60 #Used for dash

    @property
    def status(self):
        return self.vehicle.description.status

    @property
    def internal_id(self):
        return self.description.internal_id

    @internal_id.setter
    def internal_id(self, value):
        self.vehicle.internal_id = value
        RawTaxi.flush(self.id)
        return value


    @status.setter
    def status(self, status):
        current_app.logger.debug("taxi status setter")
        self.vehicle.description.status = status
        if not self.current_hail_id:
            return
        new_status, new_hail_id = self.get_new_hail_status(
            self.current_hail_id, status, self.current_hail.status)
        if new_status is not None:
            self.current_hail.status = new_status
            self.current_hail_id = new_hail_id

    @classmethod
    def get_new_hail_status(cls, current_hail_id, status, hail_status):
        if status in ('free', 'off'):
            if hail_status in ('accepted_by_customer', 'customer_on_board'):
                return ('finished', None)
        if status == 'occupied':
            if hail_status == 'accepted_by_customer':
                return ('customer_on_board', current_hail_id)
        return (hail_status, current_hail_id)


    def is_free(self, min_time=None):
        return self._is_free(self.vehicle.descriptions,
                lambda desc: User.query.get(desc.added_by).email,
                lambda desc: desc.status,
                min_time)

    def set_free(self):
#For debugging purposes
        for desc in self.vehicle.descriptions:
            desc.status = 'free'

    @property
    def driver_professional_licence(self):
        return self.driver.professional_licence

    @property
    def vehicle_licence_plate(self):
        return self.vehicle.licence_plate

    @property
    def ads_numero(self):
        return self.ads.numero

    @property
    def driver_insee(self):
        return self.ads.insee

    @property
    def driver_departement(self):
        return self.driver.departement


    map_hail_status_taxi_status = {'emitted': 'free',
            'received': 'answering',
            'sent_to_operator': 'answering',
            'received_by_operator': 'answering',
            'received_by_taxi': 'answering',
            'accepted_by_taxi': 'answering',
            'accepted_by_customer': 'oncoming',
            'declined_by_taxi': 'off',
            'declined_by_customer': 'free',
            'incident_customer': 'free',
            'incident_taxi': 'off',
            'timeout_customer': 'free',
            'timeout_taxi': 'off',
            'outdated_customer': 'free',
            'outdated_taxi': 'free',
            'failure': 'off',
            'customer_banned': None}

    def synchronize_status_with_hail(self, hail):
        if hail._status in ('declined_by_taxi', 'declined_by_customer',
                           'incident_customer', 'incident_taxi', 'timeout_customer',
                           'timeout_taxi', 'outdated_customer', 'outdated_taxi',
                            'failure', 'customer_banned'):
            self.current_hail_id = None
        next_status = self.map_hail_status_taxi_status.get(hail._status, None)
        if not next_status:
            return
        description = self.vehicle.get_description(hail.operateur)
        description.status = next_status
        RawTaxi.flush(self.id)



class RawTaxi(object):
    region = 'taxis_cache_sql'
    fields_get = {
        "taxi": get_columns_names(Taxi),
        "model": get_columns_names(Model),
        "constructor": get_columns_names(Constructor),
        "vehicle_description": get_columns_names(VehicleDescription),
        "vehicle": get_columns_names(Vehicle),
        '"ADS"': get_columns_names(ADS),
        "driver": get_columns_names(Driver),
        "departement": get_columns_names(Departement),
        "u": ['email']
    }

    request_in = """SELECT {} FROM taxi
LEFT OUTER JOIN vehicle ON vehicle.id = taxi.vehicle_id
LEFT OUTER JOIN vehicle_description ON vehicle.id = vehicle_description.vehicle_id
LEFT OUTER JOIN model ON model.id = vehicle_description.model_id
LEFT OUTER JOIN constructor ON constructor.id = vehicle_description.constructor_id
LEFT OUTER JOIN "ADS" ON "ADS".id = taxi.ads_id
LEFT OUTER JOIN driver ON driver.id = taxi.driver_id
LEFT OUTER JOIN departement ON departement.id = driver.departement_id
LEFT OUTER JOIN "user" AS u ON u.id = vehicle_description.added_by
WHERE taxi.id IN %s ORDER BY taxi.id""".format(", ".join(
    [", ".join(["{0}.{1} AS {2}_{1}".format(k, v2, k.replace('"', '')) for v2 in v])
        for k, v  in fields_get.items()])
    )

    @staticmethod
    def generate_dict(taxi_db, taxi_redis=None, operator=None, min_time=None,
                      favorite_operator=None, position=None, distance=None,
                      timestamps=None):
        if not taxi_db:
            return None
        taxi_id = taxi_db[0]['taxi_id']
        if not taxi_db[0]['taxi_ads_id']:
            current_app.logger.debug('Taxi {} has no ADS'.format(taxi_id))
            return None
        if taxi_redis:
            operator, timestamp = taxi_redis.get_operator(min_time, favorite_operator)
            if not operator:
                current_app.logger.debug('Unable to find operator for taxi {}'.format(taxi_id))
                return None
        elif timestamps:
            timestamp, operator = -1, None
            for t, ts in izip(taxi_db, timestamps):
                if not ts:
                    continue
                if favorite_operator and t['u_email'] == favorite_operator:
                    timestamp, operator = ts, favorite_operator
                    break
                if ts > timestamp:
                    timestamp, operator = ts, t['u_email']
        else:
            timestamp = None
        taxi = None
        for t in taxi_db:
            if t['u_email'] == operator:
                taxi = t
                break
        if not taxi:
            return None
        characs = VehicleDescription.get_characs(
                lambda o, f: o.get('vehicle_description_{}'.format(f)), t)
        return {
            "id": taxi_id,
            "internal_id": t['vehicle_description_internal_id'],
            "operator": t['u_email'],
            "position": taxi_redis.coords if taxi_redis else position,
            "vehicle": {
                "model": taxi['model_name'],
                "constructor": taxi['constructor_name'],
                "color": taxi['vehicle_description_color'],
                "characteristics": characs,
                "nb_seats": taxi['vehicle_description_nb_seats'],
                "licence_plate": taxi['vehicle_licence_plate'],
                "type": taxi['vehicle_description_type_'],
                "cpam_conventionne": taxi['vehicle_description_cpam_conventionne'],
                "engine": taxi['vehicle_description_engine'],
            },
            "ads": {
                "insee": taxi['ads_insee'],
                "numero": taxi['ads_numero']
            },
            "driver": {
                "departement": taxi['departement_numero'],
                "professional_licence": taxi['driver_professional_licence']
            },
            "last_update": timestamp,
            "crowfly_distance": float(taxi_redis.distance) if taxi_redis else distance,
            "rating": 4.5,
            "status": taxi['vehicle_description_status']
        }

    @staticmethod
    def filter_operateur_id(l, operateur_id):
        return [v for v in l
                if not operateur_id or v['vehicle_description_added_by'] == operateur_id
        ]


    @staticmethod
    def get(ids=None, operateur_id=None,id_=None):
        return [RawTaxi.filter_operateur_id(l, operateur_id)
                for l in cache_in(RawTaxi.request_in, ids,
                            RawTaxi.region, get_id=lambda v: v[0]['taxi_id'],
                            transform_result=lambda r: map(lambda v: list(v[1]),
                            groupby(r, lambda t: t['taxi_id']),))
               if l]

    @staticmethod
    def flush(id_):
        region = current_app.extensions['dogpile_cache'].get_region(RawTaxi.region)
        region.delete((RawTaxi.region, id_))
