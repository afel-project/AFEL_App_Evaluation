# -*- coding: utf-8 -*-
#Author: Rémi Venant
from abc import abstractmethod

from rdflib import Graph


class TracesParser:
    @abstractmethod
    def load(self, f, *args, **kwargs):
        pass

    @abstractmethod
    def dump_to_graph(self, graph: Graph, *args, **kwargs):
        pass