# -*- coding: utf-8 -*-
from . import db
from APITaxi_utils.mixins import HistoryMixin, AsDictMixin
from sqlalchemy.ext.declarative import declared_attr
from flask_security import current_user



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

    def __init__(self, customer_id, *args, **kwargs):
        db.Model.__init__(self)
        HistoryMixin.__init__(self)
        super(self.__class__, self).__init__(**kwargs)
        self.id = customer_id
        self.moteur_id = current_user.id
        self.added_via = 'api'
