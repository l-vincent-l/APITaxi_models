# -*- coding: utf-8 -*-
from . import db
from APITaxi_utils.mixins import (GetOr404Mixin, AsDictMixin, HistoryMixin,
    FilterOr404Mixin)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy_defaults import Column

class Driver(HistoryMixin, db.Model, AsDictMixin, FilterOr404Mixin):
    public_relations = ['departement']
    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))
    def __init__(self, **kwargs):
        db.Model.__init__(self, **kwargs)
        HistoryMixin.__init__(self)

    id = Column(db.Integer, primary_key=True)
    last_name = Column(db.String(255), label='Nom', description=u'Nom du conducteur')
    first_name = Column(db.String(255), label=u'Prénom',
            description=u'Prénom du conducteur')
    birth_date = Column(db.Date(),
        label=u'Date de naissance (format année-mois-jour)',
        description=u'Date de naissance (format année-mois-jour)')
    professional_licence = Column(db.String(),
            label=u'Numéro de la carte professionnelle',
            description=u'Numéro de la carte professionnelle')

    departement_id = Column(db.Integer, db.ForeignKey('departement.id'),
            nullable=True)
    departement = db.relationship('Departement', backref='vehicle',
            lazy="joined")


    @classmethod
    def can_be_listed_by(cls, user):
        return super(Driver, cls).can_be_listed_by(user) or user.has_role('prefecture')

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<drivers %r>' % unicode(self.id)
