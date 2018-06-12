# -*- coding: utf-8 -*-
# author: Rémi Venant
import logging
from abc import ABCMeta
from collections import defaultdict
import ujson as json
import datetime
import pytz
import urllib.parse as urlparse
from rdflib.namespace import RDF, URIRef
from rdflib import Literal, Graph
from .baseClasses import RdfRepresentation
from ..common.namespaces import AfelNamespacesManager, concatenate_uriref
from .learners import LearnerMappingParser

__all__ = ['AfelAppTracesParser']

LOG = logging.getLogger(__name__)

AFEL_URL = 'http://afel-project.eu/'


class AfelAppEvent(RdfRepresentation, metaclass=ABCMeta):
    """
    Abstract class to represent an AFEL App trace
    """
    def __init__(self, trace):
        self.id = trace['_id']
        self.user_id = trace['user_id']
        self.user = trace['user']
        self.start_date = self.end_date = trace['time']
        self.label = trace['label']
        self.message = trace['message']

    def complete_dump(self, activity, graph: Graph) -> int:
        ans = AfelNamespacesManager().afel_ns
        schema_ns = AfelNamespacesManager().schema_ns
        graph.add((activity, ans.user, self.user.rdf))
        graph.add((activity, ans.eventID, Literal(self.id)))
        graph.add((activity, ans.eventStartDate, Literal(self.start_date)))
        graph.add((activity, ans.eventEndDate, Literal(self.end_date)))
        graph.add((activity, schema_ns.location, Literal(AFEL_URL)))
        return 5


class AfelAppArtifactView(AfelAppEvent):
    """
    Represent a Artifact viewed trace
    The trace will be mapped to an ArtifactView and an Artifact URIRef.
    """
    def __init__(self, trace):
        super().__init__(trace)
        self.artifact_url = trace['label']
        self.artifact_content = trace['message']

    @property
    def rdf(self) -> URIRef:
        ans = AfelNamespacesManager().afel_ns
        return concatenate_uriref(ans.ArtifactView, self.id)

    def dump_to_graph(self, graph: Graph) -> int:
        ans = AfelNamespacesManager().afel_ns
        # Create activity
        activity = self.rdf
        graph.add((activity, RDF.type, ans.ArtifactView))
        # Create item viewed
        item_viewed = concatenate_uriref(ans.Artifact, urlparse.quote(self.artifact_url.strip()))
        graph.add((item_viewed, RDF.type, ans.Artifact))
        graph.add((item_viewed, ans.resourceID, Literal(self.artifact_url.strip())))
        graph.add((item_viewed, ans.URL, Literal(self.artifact_url)))
        graph.add((item_viewed, ans.content, Literal(self.artifact_content)))
        # Map item viewed to the activity
        graph.add((activity, ans.artifact, item_viewed))
        return self.complete_dump(activity, graph) + 6


class AfelAppRecommendedArtifactView(AfelAppEvent):
    """
    Represent a Recommended Artifact viewed trace.
    The trace will be mapped to a RecommendedArtifactView URIRef.
    """
    def __init__(self, trace):
        super().__init__(trace)
        self.artifact_url = trace['label']
        self.artifact_content = trace['message']

    @property
    def rdf(self) -> URIRef:
        ext_ans = AfelNamespacesManager().ext_afel_ns
        return concatenate_uriref(ext_ans.RecommendedArtifactView, self.id)

    def dump_to_graph(self, graph: Graph) -> int:
        ans = AfelNamespacesManager().afel_ns
        ext_ans = AfelNamespacesManager().ext_afel_ns
        # Create activity
        activity = self.rdf
        graph.add((activity, RDF.type, ext_ans.RecommendedArtifactView))
        # Create item viewed
        item_viewed = concatenate_uriref(ans.Artifact, urlparse.quote(self.artifact_url.strip()))
        graph.add((item_viewed, RDF.type, ans.Artifact))
        graph.add((item_viewed, ans.resourceID, Literal(self.artifact_url.strip())))
        graph.add((item_viewed, ans.URL, Literal(self.artifact_url)))
        graph.add((item_viewed, ans.content, Literal(self.artifact_content)))
        # Map item viewed to the activity
        graph.add((activity, ans.artifact, item_viewed))
        return self.complete_dump(activity, graph) + 6


class AfelAppGoBack(AfelAppEvent):
    """
    Represent a 'Back' trace (when a user goes back in a previous interface in the application).
    The trace will be mapped to a GoBack URIRef.
    """
    def __init__(self, trace):
        super().__init__(trace)
        self.destination = trace['label']
        self.comment = trace['message']

    @property
    def rdf(self):
        ext_ans = AfelNamespacesManager().ext_afel_ns
        return concatenate_uriref(ext_ans.GoBack, self.id)

    def dump_to_graph(self, graph: Graph):
        ext_ans = AfelNamespacesManager().ext_afel_ns
        # Create activity
        activity = self.rdf
        graph.add((activity, RDF.type, ext_ans.GoBack))
        graph.add((activity, ext_ans.destination, Literal(self.destination)))
        return self.complete_dump(activity, graph) + 2


class AfelAppDisplayChange(AfelAppEvent):
    """
    Represent a display change trace (when a user changes the visualisation displayed).
    The trace will be mapped to a DisplayChange URIRef.
    """
    def __init__(self, trace):
        super().__init__(trace)
        self.display = trace['label']
        self.comment = trace['message']

    @property
    def rdf(self):
        ext_ans = AfelNamespacesManager().ext_afel_ns
        return concatenate_uriref(ext_ans.DisplayChange, self.id)

    def dump_to_graph(self, graph: Graph):
        ext_ans = AfelNamespacesManager().ext_afel_ns
        # Create activity
        activity = self.rdf
        graph.add((activity, RDF.type, ext_ans.DisplayChange))
        graph.add((activity, ext_ans.display, Literal(self.display)))
        return self.complete_dump(activity, graph) + 2


class AfelAppViewScope(AfelAppEvent):
    """
    Represent a scope viewed trace (when a user views a specific scope).
    The trace will be mapped to an ArtifactView and an Artifact URIRef.
    """
    def __init__(self, trace):
        super().__init__(trace)
        self.scope = trace['label']
        self.comment = trace['message']

    @property
    def rdf(self):
        ext_ans = AfelNamespacesManager().ext_afel_ns
        return concatenate_uriref(ext_ans.ScopeView, self.id)

    def dump_to_graph(self, graph: Graph):
        ans = AfelNamespacesManager().afel_ns
        ext_ans = AfelNamespacesManager().ext_afel_ns
        # Create activity
        activity = self.rdf
        graph.add((activity, RDF.type, ext_ans.ScopeView))
        # Create item viewed
        item_viewed = concatenate_uriref(ans.Artifact, urlparse.quote(self.scope.strip()))
        graph.add((item_viewed, RDF.type, ans.Artifact))
        graph.add((item_viewed, ans.resourceID, Literal(self.scope.strip())))
        graph.add((item_viewed, ans.content, Literal(self.comment)))
        # Map item viewed to the activity
        graph.add((activity, ans.artifact, item_viewed))
        return self.complete_dump(activity, graph) + 5


class AfelAppTracesParser:
    """
    The parser to load a json file of AFEL App traces and create related RDF triples
    """
    _TIMEZONE = pytz.timezone('UTC')

    def __init__(self):
        self._activities = []

    def load_and_dump(self, fin, learners_parser: LearnerMappingParser,  graph: Graph) -> int:
        self.load(fin, learners_parser)
        return self.dump_to_graph(graph)

    def load(self, f, learners_parser: LearnerMappingParser):
        raw_traces = json.load(f)
        raw_traces = raw_traces['hits']['hits']

        traces = sorted((self._process_raw_trace(rt, learners_parser) for rt in raw_traces), key=lambda x: x['time'])
        LOG.debug("%d AFEL traces read." % len(traces))
        self._process_traces(traces)

    def dump_to_graph(self, graph: Graph) -> int:
        LOG.debug("Going to dump %d AFEL traces into RDF" % len(self._activities))
        return sum((a.dump_to_graph(graph) for a in self._activities))

    def _process_traces(self, traces):
        action_type_mapper = defaultdict(lambda: (lambda x: None))
        action_type_mapper['activitycheck'] = AfelAppArtifactView
        action_type_mapper['back'] = AfelAppGoBack
        action_type_mapper['displaychange'] = AfelAppDisplayChange
        action_type_mapper['view scope'] = AfelAppViewScope
        action_type_mapper['recocheck'] = AfelAppRecommendedArtifactView

        for trace in traces:
            action_type = trace['type']
            activity = action_type_mapper[action_type](trace)
            if activity is not None:
                self._activities.append(activity)

    @classmethod
    def _process_raw_trace(cls, rt, learners_parser: LearnerMappingParser):
        tr = rt['_source']
        tr['_id'] = rt['_id']
        dt = datetime.datetime.fromtimestamp(tr['time'] // 1000)  # convert UTC unix TS im ms to naive dt in sec.
        tr['time'] = cls._TIMEZONE.localize(dt).astimezone(pytz.utc)  # convert naive dt into aware dt
        tr['user_id'] = tr['user']
        tr['user'] = learners_parser.get_user_by_userid(tr['user_id'])
        return tr


if __name__ == '__main__':
    from ..common.utils import get_default_loggin_config
    get_default_loggin_config(logging.DEBUG)
    LOG.info("No test to do.")
