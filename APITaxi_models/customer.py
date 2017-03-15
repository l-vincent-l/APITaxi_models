# -*- coding: utf-8 -*-
from . import db
from APITaxi_utils.mixins import HistoryMixin, AsDictMixin
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from flask_security import current_user
from datetime import datetime, timedelta



class Customer(HistoryMixin, db.Model, AsDictMixin):
    @declared_attr
    def added_by(cls):
        return db.Column(db.Integer,db.ForeignKey('user.id'))
    id = db.Column(db.String, primary_key=True)
    moteur_id = db.Column(db.Integer, db.ForeignKey('user.id'),
                             primary_key=True)
    phone_number = db.Column(db.String, nullable=True)
    reprieve_begin = db.Column(db.DateTime, nullable=True)
    reprieve_end = db.Column(db.DateTime, nullable=True)
    ban_begin = db.Column(db.DateTime, nullable=True)
    ban_end = db.Column(db.DateTime, nullable=True)


    def __init__(self, *args, **kwargs):
        db.Model.__init__(self, *args, **kwargs)
        HistoryMixin.__init__(self)
        self.added_via = 'api'


    @hybrid_property
    def reprieve_duration(self):
        if self.reprieve_end and self.reprieve_begin:
            return self.reprieve_end - self.reprieve_begin
        else:
            return timedelta()


    @hybrid_property
    def reprieved(self):
        return self.reprieve_end is not None and self.reprieve_end >= datetime.now()


    @hybrid_method
    def set_ban_reprieved(self, reporting_customer):
        previous_duration = self.reprieve_duration
        if reporting_customer:
            self.reprieve_end = datetime.now() + previous_duration * 8
        else:
            self.reprieve_end = datetime.now() + previous_duration * 6
        if self.reprieve_end >= datetime.now():
            self.ban_begin = datetime.now()
            self.ban_end = datetime.now() + previous_duration / 2


    @hybrid_method
    def set_ban_non_reprieved(self, reporting_customer):
        if reporting_customer:
            self.reprieve_end = datetime.now() + timedelta(hours=2)
            self.ban_begin = datetime.now()
            self.ban_end = datetime.now() + timedelta(hours=1)
        else:
            self.reprieve_end = datetime.now() + timedelta(hours=4)


    @hybrid_method
    def set_ban(self, reporting_customer):
        self.reprieve_begin = datetime.now()
        if self.reprieved:
            self.set_ban_reprieved(reporting_customer)
        else:
            self.set_ban_non_reprieved(reporting_customer)
