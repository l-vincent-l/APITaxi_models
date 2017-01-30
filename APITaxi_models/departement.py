# -*- coding: utf-8 -*-
from . import db
from sqlalchemy_defaults import Column
from APITaxi_utils.mixins import MarshalMixin, FilterOr404Mixin

class Departement(db.Model, MarshalMixin, FilterOr404Mixin):
    id = Column(db.Integer, primary_key=True)
    nom = Column(db.String(255), label='Nom')
    numero = Column(db.String(3), label='Numero')

    def __str__(self):
        return '%s' % (self.numero)
