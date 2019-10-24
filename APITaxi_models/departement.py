# -*- coding: utf-8 -*-
from . import db
from sqlalchemy_defaults import Column
from sqlalchemy import Index
from APITaxi_utils.mixins import MarshalMixin, FilterOr404Mixin

class Departement(db.Model, MarshalMixin, FilterOr404Mixin):
    id = Column(db.Integer, primary_key=True)
    nom = Column(db.String(255), label='Nom')
    numero = Column(db.String(3), label='Numero', unique=True)

    def __str__(self):
        return '%s' % (self.numero)


departement_numero_index = Index('departement_numero_index', Departement.numero)