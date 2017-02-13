# -*- coding: utf-8 -*-
from . import db, Departement
from APITaxi_utils.mixins import (GetOr404Mixin, AsDictMixin, HistoryMixin,
    FilterOr404Mixin)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy_defaults import Column
from flask_restplus import abort, fields

class Driver(db.Model, HistoryMixin, AsDictMixin, FilterOr404Mixin):
    _additionnal_keys = ['departement']

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
    __departement = db.relationship('Departement', backref='vehicle',
            lazy="joined")

    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))

    def __init__(self, *args, **kwargs):
        db.Model.__init__(self, *args, **kwargs)
        HistoryMixin.__init__(self)

    @property
    def departement(self):
        return self.__departement

    @departement.setter
    def departement(self, kwargs):
        if "nom" in kwargs:
            self.__departement = Departement.filter_by_or_404(nom=kwargs["nom"])
        elif "numero" in kwargs:
            self.__departement = Departement.filter_by_or_404(numero=kwargs["numero"])
        else:
            abort(404, message="Unable to find departement: {}".format(kwargs))

    @classmethod
    def can_be_listed_by(cls, user):
        return super(Driver, cls).can_be_listed_by(user) or user.has_role('prefecture')

    @classmethod
    def marshall_obj(cls, show_all=False, filter_id=False, level=0, api=None):
        if level == 2:
            return {}
        r = super(Driver, cls).marshall_obj(show_all, filter_id, level+1, api)
        r['departement'] = fields.Nested(api.model("departement", Departement.marshall_obj(
            show_all, filter_id, level=level+1, api=api)))
        return r

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<drivers %r>' % unicode(self.id)
