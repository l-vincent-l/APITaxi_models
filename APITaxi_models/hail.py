# -*- coding: utf-8 -*-
from .taxis import Taxi as TaxiM, RawTaxi, TaxiRedis
from flask_security import login_required, roles_accepted,\
        roles_accepted, current_user
from flask_restplus import abort
from datetime import datetime, timedelta
from APITaxi_utils import fields, influx_db
from APITaxi_utils.mixins import GetOr404Mixin, HistoryMixin, AsDictMixin
from APITaxi_utils.caching import CacheableMixin, query_callable
from APITaxi_utils.get_short_uuid import get_short_uuid
from . import db, Customer, security
from .security import User
from flask_principal import RoleNeed, Permission
from sqlalchemy.orm import validates, joinedload, lazyload
from flask import g, current_app, request
from sqlalchemy.ext.declarative import declared_attr
from functools import wraps
from datetime import datetime, timedelta
import json, time, math
from sqlalchemy.sql.expression import text
from sqlalchemy import func
from dateutil.relativedelta import relativedelta
from math import exp, fsum
from itertools import izip

new_version_statuses = ['finished', 'customer_on_board',
                        'timeout_accepted_by_customer']
status_enum_list = [ 'emitted', 'received', 'sent_to_operator',
 'received_by_operator', 'received_by_taxi', 'timeout_taxi', 'accepted_by_taxi',
 'timeout_customer', 'declined_by_taxi', 'accepted_by_customer',
 'incident_customer', 'incident_taxi', 'declined_by_customer', 'outdated_customer',
 'outdated_taxi', 'failure'#This may be redundant
 , 'customer_banned'] + new_version_statuses 


rating_ride_reason_enum = ['ko', 'payment', 'courtesy', 'route', 'cleanliness',
                           'late', 'no_credit_card', 'bad_itinerary', 'dirty_taxi',
                          'automatic_rating']
reporting_customer_reason_enum = ['ko', 'payment', 'courtesy', 'route', 'cleanliness',
                                  'late', 'aggressive', 'no_show']
incident_customer_reason_enum = ['',
                                 'mud_river', 'parade', 'earthquake']
incident_taxi_reason_enum = ['no_show', 'address', 'traffic', 'breakdown',
                             'traffic_jam', 'garbage_truck']

class Hail(HistoryMixin, CacheableMixin, db.Model, AsDictMixin, GetOr404Mixin):
    @declared_attr
    def added_by(cls):
        return db.Column(db.Integer,db.ForeignKey('user.id'))


    cache_label = 'hails'
    query_class = query_callable()
    public_fields = ['creation_datetime', 'customer_address', 'customer_id',
        'customer_lat', 'customer_lon', 'customer_phone_number', 'id',
        'incident_customer_reason', 'incident_taxi_reason', 'last_status_change',
        'operateur', 'rating_ride', 'rating_ride_reason', 'reporting_customer',
        'reporting_customer_reason', 'status', 'taxi', 'taxi_phone_number']

    id = db.Column(db.String, primary_key=True)
    creation_datetime = db.Column(db.DateTime, nullable=False,
                                 default=datetime.utcnow,
                                 server_default=func.now())
    operateur_id = db.Column(db.Integer, db.ForeignKey('user.id'),
            nullable=True)
    _operateur = db.relationship('User', 
        primaryjoin=(operateur_id==User.id), lazy='joined')
    customer_id = db.Column(db.String,
                            nullable=False)
    customer_lon = db.Column(db.Float, nullable=False)
    customer_lat = db.Column(db.Float, nullable=False)
    customer_address = db.Column(db.String, nullable=False)
    customer_phone_number = db.Column(db.String, nullable=False)
    taxi_id = db.Column(db.String,
                        db.ForeignKey('taxi.id', name='hail_taxi_id', use_alter=True),
                        nullable=False)
    taxi_relation = db.relationship('Taxi',
                            backref="taxi", lazy="joined",
                            foreign_keys=taxi_id)
    _status = db.Column(db.Enum(*status_enum_list,
                        name='hail_status'),
                        default='emitted', nullable=False, name='status')
    last_status_change = db.Column(db.DateTime, default=datetime.now())
    db.ForeignKeyConstraint(['operateur_id', 'customer_id'],
        ['customer.operateur_id', 'customer.id'],
        )
    taxi_phone_number = db.Column(db.String, nullable=True)
    rating_ride = db.Column(db.Integer)
    rating_ride_reason = db.Column(db.Enum(*rating_ride_reason_enum,
      name='reason_ride_enum'), nullable=True)
    incident_customer_reason = db.Column(db.Enum(*incident_customer_reason_enum,
        name='incident_customer_reason_enum'), nullable=True)
    incident_taxi_reason = db.Column(db.Enum(*incident_taxi_reason_enum,
        name='incident_taxi_reason_enum'), nullable=True)
# Reporting of the customer by the taxi
    reporting_customer = db.Column(db.Boolean, nullable=True)
    reporting_customer_reason = db.Column(db.Enum(*reporting_customer_reason_enum,
        name='reporting_customer_reason_enum'), nullable=True)
    initial_taxi_lon = db.Column(db.Float, nullable=True)
    initial_taxi_lat = db.Column(db.Float, nullable=True)
    change_to_sent_to_operator = db.Column(db.DateTime, nullable=True)
    change_to_received_by_operator = db.Column(db.DateTime, nullable=True)
    change_to_received_by_taxi = db.Column(db.DateTime, nullable=True)
    change_to_accepted_by_taxi = db.Column(db.DateTime, nullable=True)
    change_to_accepted_by_customer = db.Column(db.DateTime, nullable=True)
    change_to_declined_by_taxi = db.Column(db.DateTime, nullable=True)
    change_to_declined_by_customer = db.Column(db.DateTime, nullable=True)
    change_to_incident_taxi = db.Column(db.DateTime, nullable=True)
    change_to_incident_customer = db.Column(db.DateTime, nullable=True)
    change_to_timeout_taxi = db.Column(db.DateTime, nullable=True)
    change_to_timeout_customer = db.Column(db.DateTime, nullable=True)
    change_to_failure = db.Column(db.DateTime, nullable=True)
    change_to_finished = db.Column(db.DateTime, nullable=True)
    change_to_customer_on_board = db.Column(db.DateTime, nullable=True)
    change_to_timeout_accepted_by_customer = db.Column(db.DateTime, nullable=True)


    def __init__(self, *args, **kwargs):
        self.id = get_short_uuid()
        status = kwargs.pop('status')
        HistoryMixin.__init__(self)

        customer = Customer.query.filter_by(id=kwargs['customer_id'],
                moteur_id=current_user.id).first()
        if not customer:
            customer = Customer(id=kwargs['customer_id'],
                                phone_number=kwargs['customer_phone_number'],
                                moteur_id=current_user.id)
            db.session.add(customer)
            db.session.commit()
        self.customer_id = customer.id
        db.Model.__init__(self, *args, **kwargs)

        if customer.ban_end and datetime.now() < customer.ban_end:
            self.status = 'customer_banned'
            db.session.add(self)
            abort(403, message='Customer is banned')

        descriptions = RawTaxi.get((kwargs['taxi_id'],), self.operateur_id)
        if len(descriptions) == 0 or len(descriptions[0]) == 0:
            g.hail_log = HailLog('POST', None, request.data)
            abort(404, message='Unable to find taxi {} of {}'.format(
                kwargs['taxi_id'], kwargs['operateur']))
        if descriptions[0][0]['vehicle_description_status'] != 'free' or\
                not TaxiRedis(kwargs['taxi_id']).is_fresh(kwargs['operateur']):
            g.hail_log = HailLog('POST', None, request.data)
            abort(403, message="The taxi is not available")
        taxi_pos = current_app.extensions['redis'].geopos(
            current_app.config['REDIS_GEOINDEX'],
            '{}:{}'.format(kwargs['taxi_id'], self.operateur.email))
        if taxi_pos:
            self.initial_taxi_lat, self.initial_taxi_lon = taxi_pos[0]
        db.session.add(self)
        db.session.commit()
        taxi = TaxiM.query.get(kwargs['taxi_id'])
        taxi.current_hail_id = self.id
        db.session.add(taxi)
        self.status = status
        self.ads_insee = descriptions[0][0]['ads_insee']


    @classmethod
    def to_exclude(cls):
        return HistoryMixin.to_exclude() + ['creation_datetime']

    @validates('rating_ride_reason')
    def validate_rating_ride_reason(self, key, value):
#We need to restrict this to a subset of statuses
        if current_user.id != self.added_by and value != 'automatic_rating':
            raise RuntimeError()
        return value


    @validates('incident_customer_reason')
    def validate_incident_customer_reason(self, key, value):
        if current_user.id != self.added_by:
            raise RuntimeError()
        self.status = 'incident_customer'
        return value

    @validates('incident_taxi_reason')
    def validate_incident_taxi_reason(self, key, value):
        if current_user.id != self.operateur_id:
            raise RuntimeError()
        self.status = 'incident_taxi'
        return value

    @validates('reporting_customer_reason')
    def validate_reporting_customer_reason(self, key, value):
        if current_user.id != self.operateur_id:
            raise RuntimeError()
        return value

    @validates('reporting_customer')
    def validate_reporting_customer(self, key, value):
        if current_user.id != self.operateur_id:
            raise RuntimeError()
        self.manage_penalty_customer(True)
        return value

    @classmethod
    def compute_total_rating(cls, ratings):
        return float(sum(
            map(
                lambda rs_f: sum(map(lambda r: r*rs_f[1], rs_f[0])),
                izip(ratings.values(), decay_factor.values())
            )
        ))

    @classmethod
    def compute_total_factor(cls, ratings):
        return fsum(map(lambda k_v: k_v[1]*len(ratings[k_v[0]]),
                                decay_factor.iteritems()))

    def init_rating(self, value):
        min_date = datetime.now() + relativedelta(months=-6)
        nb_days = (datetime.now() - min_date).days
        ratings = {i: [] for i in range(nb_days)}
        ratings[0] = [value]
        HailModel = self.__class__
        for hail_ in HailModel.query.filter_by(taxi_id=self.taxi_id)\
                    .filter(HailModel.creation_datetime >= min_date)\
                    .filter(HailModel.rating_ride != None):
            key = nb_days - (hail_.creation_datetime - min_date).days - 1
            ratings[key].append(hail_.rating_ride)
        #We want to fill the ratings when there is no value
        ratings = {k: v+[4.5]*(3-len(v)) for k, v in ratings.iteritems()}
        return ratings

    @validates('rating_ride')
    def validate_rating_taxi(self, key, value):
#We need to restrict this to a subset of statuses
        assert 1 <= value <= 5, 'Rating value has to be 1 <= value <= 5'
        if self.rating_ride == value:
            return value
        ratings = self.init_rating(value)
        decay_factor = {nb_days-i-1:exp(-float(nb_days-i)/30.) for i in range(nb_days)}
        total_rating = self.compute_total_rating(ratings)
        total_factor = self.compute_total_factor(ratings)
        self.taxi_relation.rating = total_rating / total_factor
        return value

    timeouts = {
            'received': (15, 'failure'),
            'sent_to_operator': (10, 'failure'),
            'received_by_operator': (10, 'failure'),
            'received_by_taxi': (30, 'timeout_taxi'),
            'accepted_by_taxi': (20, 'timeout_customer'),
            'accepted_by_customer': (30*60, 'timeout_accepted_by_customer')
    }

    roles_accepted = {
            'received': ['moteur', 'admin'],
            'received_by_taxi': ['operateur', 'admin'],
            'accepted_by_taxi': ['operateur', 'admin'],
            'declined_by_taxi': ['operateur', 'admin'],
            'incident_taxi': ['operateur', 'admin'],
            'incident_customer': ['moteur', 'admin'],
            'accepted_by_customer': ['moteur', 'admin'],
            'declined_by_customer': ['moteur', 'admin'],
    }


    status_required = {
            'sent_to_operator': ['received'],
            'received_by_operator': ['received'],
            'received_by_taxi': ['received_by_operator', 'received'],
            'accepted_by_taxi': ['received_by_taxi'],
            'declined_by_taxi': ['received_by_taxi'],
            'accepted_by_customer': ['accepted_by_taxi'],
            'declined_by_customer': ['emitted', 'received', 'sent_to_operator',
                'received_by_operator', 'received_by_taxi', 'accepted_by_taxi'],
    }

    @property
    def status(self):
        time, next_status = self.timeouts.get(self._status, (None, None))
        if time:
            self.check_time_out(time, next_status)
        if self._status in new_version_statuses and g.version <= 2:
            change_list = [
                'change_to_sent_to_operator', 'change_to_received_by_operator',
                'change_to_received_by_taxi', 'change_to_accepted_by_taxi',
                'change_to_accepted_by_customer', 'change_to_declined_by_taxi',
                'change_to_declined_by_customer', 'change_to_incident_taxi',
                'change_to_incident_customer', 'change_to_timeout_taxi',
                'change_to_timeout_customer', 'change_to_failure'
            ]
            basetime = datetime(1970, 1, 1)
            last_change = max(change_list,
                              key=lambda c: getattr(self, c) or basetime)
            return last_change[len('change_to_'):]
        return self._status

    def check_role_accepted(self, value):
        roles_accepted = self.roles_accepted.get(value, None)
        if roles_accepted:
            perm = Permission(*[RoleNeed(role) for role in roles_accepted])
            if not perm.can():
                raise RuntimeError("You're not authorized to set this status")

    def check_status_required(self, value):
        status_required = self.status_required.get(value, None)
        if status_required and self._status not in status_required:
            raise ValueError("You cannot set status from {} to {}".format(
                self._status, value))

    def value_settable(self, value):
        if self._status is None:
            return True
        if value.startswith('incident') or value.startswith('reporting'):
            return True
        old_status_index = status_enum_list.index(value)
        new_status_index = status_enum_list.index(self._status)
        return old_status_index > new_status_index

    @status.setter
    def status(self, value):
        previous_status = self._status
        if not value in status_enum_list:
            raise AssertionError("Invalid status, {} is not in {}".format(value, status_enum_list))
        if value == self._status:
            return True
        self.check_role_accepted(value)
        self.check_status_required(value)
        if self.value_settable(value):
            self._status = value
        self.manage_penalty_customer()
        self.manage_penalty_taxi()

        self.status_changed()
        taxi = TaxiM.cache.get(self.taxi_id)
        taxi.synchronize_status_with_hail(self)
        influx_db.write_point(current_app.config['INFLUXDB_TAXIS_DB'],
                              "hails_status_changed",
                              {
                                  "added_by": User.query.get(self.added_by).email,
                                  "operator": self.operateur.email,
                                  "zupc": taxi.ads.zupc.insee,
                                  "previous_status": previous_status,
                                  "status": self._status
                               }
        )

    def status_changed(self):
        self.last_status_change = datetime.now()
        field = 'change_to_{}'.format(self.status)
        if hasattr(self, field):
            setattr(self, field, self.last_status_change)


    def check_time_out(self, duration, timeout_status):
        if datetime.now() < (self.last_status_change + timedelta(seconds=duration)):
            return True
        self.status = timeout_status
        db.session.commit()
        return False

    def manage_penalty_taxi(self):
        if self._status not in ('timeout_taxi', 'declined_by_taxi'):
            return
        if not current_app.config['AUTOMATIC_RATING_ACTIVATED']:
            return
        self.rating_ride_reason = 'automatic_rating'
        self.rating_ride = current_app.config['AUTOMATIC_RATING']

    def manage_penalty_customer(self, reporting_customer=False):
        if self._status not in ('timeout_customer', 'declined_by_customer', 
                            'incident_customer', 'accepted_by_customer'):
            return
        customer = Customer.query.filter_by(id=self.customer_id,
                moteur_id=self.added_by).first()
        if customer.reprieve_end and customer.reprieve_begin:
            previous_duration = customer.reprieve_end - customer.reprieve_begin
        else:
            previous_duration = timedelta()
        customer.reprieve_begin = datetime.now()
        if not customer.reprieve_end or customer.reprieve_end < datetime.now():
            if reporting_customer:
                customer.reprieve_end = datetime.now() + timedelta(hours=2)
                customer.ban_begin = datetime.now()
                customer.ban_end = datetime.now() + timedelta(hours=1)
            else:
                customer.reprieve_end = datetime.now() + timedelta(hours=4)
        else:
            if reporting_customer:
                customer.reprieve_end = datetime.now() + previous_duration * 8
            else:
                customer.reprieve_end = datetime.now() + previous_duration * 6
            if customer.reprieve_end >= datetime.now():
                customer.ban_begin = datetime.now()
                customer.ban_end = datetime.now() + previous_duration / 2

    def to_dict(self):
        self.check_time_out()
        return self.as_dict()

    @property
    def taxi(self):
        carac = TaxiM.retrieve_caracs(self.taxi_id).get(self.operateur.email, None)
        if not carac:
            return {}
        return {
            'position': {'lon': carac['lon'],'lat' : carac['lat']},
            'last_update' : carac['timestamp'],
            'id': self.taxi_id
        }

    @property
    def operateur(self):
        return User.query.get(self.operateur_id)

    @operateur.setter
    def operateur(self, value):
        operateur = security.User.filter_by_or_404(
                email=value,
                message='Unable to find the taxi\'s operateur')
        self.operateur_id = operateur.id


    @classmethod
    def get_or_404(cls, hail_id):
        m = Hail.query.from_statement(
            text("SELECT * FROM hail where id=:hail_id")
        ).params(hail_id=hail_id).one()
        if not m:
            abort(404, "Unable to find hail: {}".format(hail_id))
        return m


class HailLog(object):
    def __init__(self, method, hail, payload):
        self.method = method
        self.initial_status = hail._status if hail else ""
        self.payload = payload
        self.datetime = time.time()
        self.id = hail.id if hail else "notposted:" + str(get_short_uuid())

    def store(self, response, redis_store, error=None):
        name = 'hail:{}'.format(self.id)
        to_store = {
                    "method": self.method,
                    "payload": self.payload,
                    "initial_status": self.initial_status,
                    "user": current_user.email if current_user else ""
        }
        if error:
            to_store['error'] = error
        else:
            to_store['return'] = response.data if hasattr(response, 'data') else response.content
            to_store['code'] = response.status_code
        redis_store.zadd(name, self.datetime, json.dumps(to_store))
        redis_store.expire(name, timedelta(weeks=6))

    @classmethod
    def after_request(cls, redis_store):
        def decorator(response):
            if not hasattr(g, 'hail_log'):
                return response
            g.hail_log.store(response, redis_store)
            return response
        return decorator
