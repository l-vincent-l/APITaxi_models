# -*- coding: utf-8 -*-
from . import db, Departement
from APITaxi_utils.mixins import (GetOr404Mixin, AsDictMixin, HistoryMixin,
    FilterOr404Mixin)
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy_defaults import Column
from sqlalchemy import Index
from flask_restplus import abort, fields

class Driver(db.Model, HistoryMixin, AsDictMixin, FilterOr404Mixin):
    _additionnal_keys = ['departement']

    id = Column(db.Integer, primary_key=True)
    last_name = Column(db.String(255), label='Nom', description='Nom du conducteur')
    first_name = Column(db.String(255), label='Prénom',
            description='Prénom du conducteur')
    birth_date = Column(db.Date(),
        label='Date de naissance (format année-mois-jour)',
        description='Date de naissance (format année-mois-jour)')
    professional_licence = Column(db.String(),
            label='Numéro de la carte professionnelle',
            description='Numéro de la carte professionnelle')

    departement_id = Column(db.Integer, db.ForeignKey('departement.id'),
            nullable=True)
    _departement = db.relationship('Departement', lazy="joined")

    @declared_attr
    def added_by(cls):
        return Column(db.Integer,db.ForeignKey('user.id'))

    def __init__(self, *args, **kwargs):
        db.Model.__init__(self, *args, **kwargs)
        HistoryMixin.__init__(self)
        current_driver = Driver.query.filter_by(
                professional_licence=kwargs['professional_licence'],
                departement_id=self.departement.id
            ).order_by(
                Driver.id.desc()
            ).first()
        if current_driver:
            self.id = current_driver.id
            db.session.merge(self)
        else:
            db.session.add(self)
        db.session.commit()

    @property
    def departement(self):
        return self._departement

    def set_from_nom(self, kwargs):
        if "nom" in kwargs and kwargs['nom'] is not None:
            self._departement = Departement.query.filter(Departement.nom.ilike(kwargs["nom"])).first()
        return self._departement is not None

    def set_from_departement(self, kwargs):
        if "numero" in kwargs and kwargs['numero'] is not None:
            self._departement = Departement.query.filter_by(numero=kwargs["numero"]).first()
        return self._departement is not None

    @departement.setter
    def departement(self, kwargs):
        if not self.set_from_nom(kwargs):
            if not self.set_from_departement(kwargs):
                abort(404, message="Unable to find departement: {}".format(kwargs))

    @classmethod
    def marshall_obj(cls, show_all=False, filter_id=False, level=0, api=None):
        if level == 2:
            return {}
        r = super(Driver, cls).marshall_obj(show_all, filter_id, level+1, api)
        from flask_restplus.model import Model
        class NoSchemaModel(Model):
            _schema = None
            is_no_schema = True
        departement_model = NoSchemaModel("departement",
                                      Departement.marshall_obj(show_all,
                                                               filter_id,
                                                               level=level+1,
                                                               api=api)
        )
        departement_model._schema = {
            'type': 'object',
            'anyOf': [
                {'nom': {'description': '', 'type': 'string'}},
                {'numero': {'description': '', 'type': 'string'}}
            ]
        }
        api.add_model("departement", departement_model)
        r['departement'] = fields.Nested(departement_model)
        return r

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<drivers %r>' % str(self.id)

driver_professional_licence_index = Index('driver_professional_licence_idx', Driver.professional_licence)
driver_departement_id_index = Index('driver_departement_id_idx', Driver.departement_id)