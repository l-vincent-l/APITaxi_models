# -*- coding: utf-8 -*-
from . import db
from APITaxi_utils.mixins import AsDictMixin, unique_constructor, MarshalMixin
from sqlalchemy_defaults import Column

@unique_constructor(db.session,
                    lambda name: name,
                    lambda query, name: query.filter(Constructor.name == name.name) if isinstance(name, Constructor) else query.filter(Constructor.name == name))
class Constructor(db.Model, AsDictMixin, MarshalMixin):
    id = Column(db.Integer, primary_key=True)
    name = Column(db.String, label=u'Dénomination commerciale de la marque',
                description=u'Dénomination commerciale de la marque',
                unique=True)

    def __init__(self, name=None):
        db.Model.__init__(self)
        if isinstance(name, self.__class__):
            self.name = name.name
        else:
            self.name = name

    def __repr__(self):
        return '<Constructor %r>' % unicode(self.name)

    def __eq__(self, other):
        return self.__repr__() == other.__repr__()

    def __ne__(self, other):
        return not self.__eq__(other)
