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
        db.session.add(self)
        db.session.commit()
        cur = db.session.connection().connection.cursor()
        cur.execute("""
                UPDATE taxi set driver_id = %s WHERE driver_id IN (
                    SELECT id FROM driver WHERE professional_licence = %s
                    AND departement_id = %s
                )""",
                (self.id, self.professional_licence, self.departement_id)
            )
        db.session.commit()

    @property
    def departement(self):
        return self.__departement

    @departement.setter
    def departement(self, kwargs):
        if "nom" in kwargs and kwargs['nom'] is not None:
            self.__departement = Departement.query.filter(Departement.nom.ilike(kwargs["nom"])).first()
            if self.__departement:
                return
        if "numero" in kwargs and kwargs['numero'] is not None:
            self.__departement = Departement.query.filter_by(numero=kwargs["numero"]).first()
            if self.__departement:
                return
        abort(404, message="Unable to find departement: {}".format(kwargs))

    @classmethod
    def can_be_listed_by(cls, user):
        return super(Driver, cls).can_be_listed_by(user) or user.has_role('prefecture')

    @classmethod
    def marshall_obj(cls, show_all=False, filter_id=False, level=0, api=None):
        if level == 2:
            return {}
        r = super(Driver, cls).marshall_obj(show_all, filter_id, level+1, api)
        departement_model = api.model("departement",
                                      Departement.marshall_obj(show_all,
                                                               filter_id,
                                                               level=level+1,
                                                               api=api)
        )
        departement_model.__schema__ = {
            u'type': 'object',
            u'anyOf': [
                {'nom': {u'description': '', u'type': u'string'}},
                {'numero': {u'description': '', u'type': u'string'}}
            ]
        }
        r['departement'] = fields.Nested(departement_model)
        return r

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return '<drivers %r>' % unicode(self.id)
