# -*- coding: utf-8 -*-
from . import db
from APITaxi_utils.mixins import AsDictMixin, unique_constructor, MarshalMixin
from sqlalchemy_defaults import Column

@unique_constructor(db.session,
                    lambda name: name,
                    lambda query, name: query.filter(Model.name == name.name) if isinstance(name, Model) else query.filter(Model.name == name))
class Model(db.Model, AsDictMixin, MarshalMixin):

    id = Column(db.Integer, primary_key=True)
    name = Column(db.String, label=u'Dénomination commerciale du modèle',
                description=u'Dénomination commerciale du modèle',
                unique=True)

    def __init__(self, name=None):
        db.Model.__init__(self)
        if isinstance(name, self.__class__):
            self.name = name.name
        else:
            self.name = name

    def __repr__(self):
        return '<Model %r>' % unicode(self.id)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)
