# -*- coding: utf-8 -*-
# author: Rémi Venant
import logging
from rdflib import Graph
from rdflib.namespace import ClosedNamespace, Namespace
from .utils import Singleton

__all__ = ['concatenate_uriref', 'AfelNamespacesManager']

LOG = logging.getLogger(__name__)

def concatenate_uriref(uriref, term):
    return uriref + '#' + term


class AfelNamespacesManager(metaclass=Singleton):
    """
    A singleton to manage AFEL, extended AFEL and Schema RDF namespaces
    """
    def __init__(self, **kwargs):
        self.init_namespaces(**kwargs)


    def init_namespaces(self, afel_source="http://data.afel-project.eu/vocab/afel_schema.rdf",
                    afel_publicID="http://vocab.afel-project.eu/",
                    ext_afel_source="./resources/afel_schema_extension.rdf",
                    ext_afel_publicID="http://vocab.afel-project.eu/extension/"):
        self._afel_ns = self.__get_closed_ns(afel_source, afel_publicID)
        self._ext_afel_ns = self.__get_closed_ns(ext_afel_source, ext_afel_publicID)
        self._schema_ns = Namespace('http://schema.org/')


    @property
    def afel_ns(self):
        return self._afel_ns

    @property
    def ext_afel_ns(self):
        return self._ext_afel_ns

    @property
    def schema_ns(self):
        return self._schema_ns

    @staticmethod
    def __get_closed_ns(source, publicID):
        g = Graph()
        g.load(source, publicID=publicID)
        names = set()
        for s, _, _ in g:
            try:
                name = g.qname(s)
                if name.startswith('ns1:'):
                    names.add(name[4:])
            except Exception as e:
                if not str(e).startswith("Can't split"):
                    raise e
        return ClosedNamespace(publicID, names)


if __name__ == '__main__':
    from .utils import get_default_loggin_config
    get_default_loggin_config(logging.DEBUG)
    LOG.info("Test Namespace manager")
    ns_mgr = AfelNamespacesManager()
    LOG.info("Schema NS: %s" % ns_mgr.schema_ns)
    LOG.info("Schema AFEL: %s" % ns_mgr.afel_ns)
    LOG.info("Schema EXT_AFEL: %s" % ns_mgr.ext_afel_ns)
    LOG.info("Test done properly.")