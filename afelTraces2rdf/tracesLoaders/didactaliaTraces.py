# -*- coding: utf-8 -*-
import logging
from collections import defaultdict
import ujson as json
import datetime
import dateutil.parser as dateparser
import urllib.parse as urlparse
from abc import ABCMeta
from rdflib.namespace import RDF
from rdflib import Literal, Graph, URIRef
from .baseClasses import RdfRepresentation
from ..common.namespaces import AfelNamespacesManager, concatenate_uriref
from .learners import LearnerMappingParser


__all__ = ['DidactaliaLearningTracesParser',]

LOG = logging.getLogger(__name__)

DIDACTALIA_URL = 'https://didactalia.net'


class DidactaliaLearningActivity(RdfRepresentation, metaclass=ABCMeta):
    """
    Abstract class to represent a didactalia trace
    """
    def __init__(self, trace):
        self.id = trace['_id']
        self.start_date = self.end_date = trace['date']
        self.user_id = trace['user_id']
        self.user = trace['user']
        self.community_id = trace['community_id']

    def complete_dump(self, activity, graph: Graph) -> int:
        ans = AfelNamespacesManager().afel_ns
        schema_ans = AfelNamespacesManager().schema_ns
        graph.add((activity, ans.user, self.user.rdf))
        graph.add((activity, ans.eventID, Literal(self.id)))
        graph.add((activity, ans.eventStartDate, Literal(self.start_date)))
        graph.add((activity, ans.eventEndDate, Literal(self.end_date)))
        graph.add((activity, schema_ans.location, Literal(DIDACTALIA_URL)))
        return 5


class ArtifactView(DidactaliaLearningActivity):
    """
    Represents the 'resourceVisited' trace, when a user open a pedagogical resource.
    The trace will be mapped to a ArtifactView UriRef, and an Artifact UriRef.
    """
    def __init__(self, trace):
        super().__init__(trace)
        self.item = trace['Item']
        self.referer_url = trace['referer_url']

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
        item_viewed = concatenate_uriref(ans.Artifact, urlparse.quote(self.item.strip()))
        graph.add((item_viewed, RDF.type, ans.Artifact))
        graph.add((item_viewed, ans.resourceID, Literal(self.item.strip())))
        graph.add((item_viewed, ans.URL, Literal(self.referer_url)))
        # Map item viewed to the activity
        graph.add((activity, ans.artifact, item_viewed))
        # Create the common triples of didactalia traces
        return self.complete_dump(activity, graph) + 5


class SearchActivity(DidactaliaLearningActivity):
    """
    Represents the 'freeTextSearch' trace, when a user submit a query for a research.
    The trace will be mapped to a Search URIRef.
    """
    def __init__(self, trace):
        super().__init__(trace)
        self.query = trace['search_text']

    @property
    def rdf(self) -> URIRef:
        ext_ans = AfelNamespacesManager().ext_afel_ns
        return concatenate_uriref(ext_ans.Search, self.id)

    def dump_to_graph(self, graph: Graph) -> int:
        ext_ans = AfelNamespacesManager().ext_afel_ns
        schema_ans = AfelNamespacesManager().schema_ns
        # Create activity
        activity = self.rdf
        graph.add((activity, RDF.type, ext_ans.Search))
        graph.add((activity, schema_ans.query, Literal(self.query)))
        # Create the common triples of didactalia traces
        return self.complete_dump(activity, graph) + 2


class FacetAddActivity(DidactaliaLearningActivity):
    """
    Represents  the 'facetsSearchAdd' trace, when a user add a facet to narrow the research.
    The trace will be mapped to a FacetAdd URIRef.
    """
    def __init__(self, trace):
        super().__init__(trace)
        self.facet = trace['facet']

    @property
    def rdf(self) -> URIRef:
        ext_ans = AfelNamespacesManager().ext_afel_ns
        return concatenate_uriref(ext_ans.FacetAdd, self.id)

    def dump_to_graph(self, graph: Graph) -> int:
        ext_ans = AfelNamespacesManager().ext_afel_ns
        # Create activity
        activity = self.rdf
        graph.add((activity, RDF.type, ext_ans.FacetAdd))
        graph.add((activity, ext_ans.facet, Literal(self.facet)))
        # Create the common triples of didactalia traces
        return self.complete_dump(activity, graph) + 2


class FacetRemoveActivity(DidactaliaLearningActivity):
    """
    Represents  the 'facetsSearchRemove' trace, when a user remove a facet to widen the research field.
    The trace will be mapped to a FacetRemove URIRef.
    """
    def __init__(self, trace):
        super().__init__(trace)
        self.facet = trace['facet']

    @property
    def rdf(self) -> URIRef:
        ext_ans = AfelNamespacesManager().ext_afel_ns
        return concatenate_uriref(ext_ans.FacetRemove, self.id)

    def dump_to_graph(self, graph: Graph) -> int:
        ext_ans = AfelNamespacesManager().ext_afel_ns
        activity = self.rdf
        graph.add((activity, RDF.type, ext_ans.FacetRemove))
        graph.add((activity, ext_ans.facet, Literal(self.facet)))
        # Create the common triples of didactalia traces
        return self.complete_dump(activity, graph) + 2


class GamePlayedActivity(DidactaliaLearningActivity):
    """
    Represents a couple 'playStart' and 'playEnd' linked by their playSession attribute.
    The two traces will be mapped into a single DidactaliaGamePlayed UriRef.
    """
    def __init__(self, trace):
        """
        Construct the instance with the playStart trace
        :param trace: a playStart trace
        """
        super().__init__(trace)
        # Common attribute of all game traces related to the same play session
        self.play_session = trace['playSession']
        self.resource_id = trace['resource_id']
        # Attributes given by the playStart trace
        self.game_language = trace['gameLanguage']
        self.label_state = trace['labelState']
        self.answers_details_state = trace['answersDetailsState']
        self.audio_state = trace['audioState']
        self.longitude = float(trace['longitude'])
        self.latitude = float(trace['latitude'])
        self.zoom_level = int(trace['zoomLevel'])
        # Attribute that will be given by the playEnd trace
        self.correct_at_first = None
        self.correct_at_second = None
        self.correct_at_third = None
        self.correct_at_fourth = None
        self.total_elements = None
        self.score = None
        # Construction of the DidactaliaGamePlayed instance, required by all the sub-event traces that can happen
        self._is_activity_achieved = False

    @property
    def rdf(self) -> URIRef:
        return concatenate_uriref(AfelNamespacesManager().ext_afel_ns.DidactaliaGamePlayed, self.id)

    def end_activity(self, trace) -> None:
        """
        Complete the activity with the playEnd related trace
        :param trace: the playEnd trace
        """
        self.correct_at_first = int(trace['correctAtFirst'])
        self.correct_at_second = int(trace['correctAtSecond'])
        self.correct_at_third = int(trace['correctAtThird'])
        self.correct_at_fourth = int(trace['correctAtFourth'])
        self.total_elements = int(trace['totalElements'])
        self.score = int(trace['score'])
        self.end_date = trace['date']
        self._is_activity_achieved = True

    def dump_to_graph(self, graph: Graph) -> None:
        ans = AfelNamespacesManager().afel_ns
        ext_ans = AfelNamespacesManager().ext_afel_ns
        # Add the activity to the graph
        activity = self.rdf
        graph.add((activity, RDF.type, ext_ans.DidactaliaGamePlayed))
        # Create the artifact related to the game
        game = concatenate_uriref(ans.Artifact, self.resource_id)
        graph.add((game, RDF.type, ans.Artifact))
        graph.add((game, ans.resourceID, Literal(self.resource_id)))
        graph.add((activity, ans.artifact, game))
        # Add the whole properties
        graph.add((activity, ext_ans.language, Literal(self.game_language)))
        graph.add((activity, ext_ans.labelState, Literal(self.label_state)))
        graph.add((activity, ext_ans.audioState, Literal(self.audio_state)))
        graph.add((activity, ext_ans.answersDetailsState, Literal(self.answers_details_state)))
        graph.add((activity, ext_ans.longitude, Literal(self.longitude)))
        graph.add((activity, ext_ans.latitude, Literal(self.latitude)))
        graph.add((activity, ext_ans.zoomLevel, Literal(self.zoom_level)))
        nb_triples = 11
        if not self._is_activity_achieved:
            LOG.debug("Game activity is going to be dumped while it is not achieved, adding one day to the start")
            oneday = datetime.timedelta(days=1)
            self.end_date = self.start_date + oneday
        else:
            graph.add((activity, ext_ans.correctAtFirst, Literal(self.correct_at_first)))
            graph.add((activity, ext_ans.correctAtSecond, Literal(self.correct_at_second)))
            graph.add((activity, ext_ans.correctAtThird, Literal(self.correct_at_third)))
            graph.add((activity, ext_ans.correctAtFourth, Literal(self.correct_at_fourth)))
            graph.add((activity, ext_ans.totalElements, Literal(self.total_elements)))
            graph.add((activity, ext_ans.score, Literal(self.score)))
            nb_triples += 6

        # Create the common triples of didactalia traces
        return self.complete_dump(activity, graph) + nb_triples


class GameAttributeChanged(DidactaliaLearningActivity):
    """
    Represents  any of the change event trace that can happend during a game session.
    The trace will be mapped to a GameAttributeChange URIRef.
    """
    def __init__(self, trace, game_played_activity: GamePlayedActivity=None):
        super().__init__(trace)
        self.game_played_activity = game_played_activity
        if trace['actionType'] == 'labelStateChange':
            self.attribute_name = 'label'
            self.attribute_value = trace['labelState']
        elif trace['actionType'] == 'languageChange':
            self.attribute_name = 'language'
            self.attribute_value = trace['gameLanguage']
        elif trace['actionType'] == 'audioStateChange':
            self.attribute_name = 'audio'
            self.attribute_value = trace['audioState']
        elif trace['actionType'] == 'answersDetailsStateChange':
            self.attribute_name = 'answersDetails'
            self.attribute_value = trace['answersDetailsState']
        elif trace['actionType'] == 'playStudyChange':
            self.attribute_name = 'playStudy'
            self.attribute_value = trace['state']
        else:
            raise Exception("Wrong application state!")

    @property
    def rdf(self) -> URIRef:
        ext_ans = AfelNamespacesManager().ext_afel_ns
        return concatenate_uriref(ext_ans.GameAttributeChange, self.id)

    def dump_to_graph(self, graph: Graph) -> None:
        ext_ans = AfelNamespacesManager().ext_afel_ns
        schema_ans = AfelNamespacesManager().schema_ns
        # Create the activity
        activity = self.rdf
        graph.add((activity, RDF.type, ext_ans.GameAttributeChange))
        graph.add((activity, ext_ans.gamePropertyName, Literal(self.attribute_name)))
        graph.add((activity, ext_ans.gamePropertyValue, Literal(self.attribute_value)))
        nb_triples = 3
        # Link the activity to the game played activity if it exists
        if self.game_played_activity is not None:
            graph.add((activity, schema_ans.superEvent, self.game_played_activity.rdf))
            nb_triples += 1
        return self.complete_dump(activity, graph) + nb_triples


class DidactaliaLearningTracesParser:
    """
    The parser to load a json file of didactalia traces and create related RDF triples
    """
    def __init__(self):
        self._activities = []

    def load_and_dump(self, fin, learners_parser: LearnerMappingParser,  graph: Graph) -> int:
        self.load(fin, learners_parser)
        return self.dump_to_graph(graph)

    def load(self, f, learners_parser: LearnerMappingParser) -> None:
        raw_traces = json.load(f)
        raw_traces = raw_traces['hits']['hits']

        # Sort traces based on their timestamp to retrieve properly related game events
        # then on some of their actiontype, since some trace have the same timestamp :(
        actionType_order = defaultdict(lambda: 1, playStart=0, playEnd=2)
        actionType_order
        traces = sorted([self._process_raw_trace(rt, learners_parser) for rt in raw_traces],
                        key=lambda x: (actionType_order[x['actionType']], x['date']))
        LOG.debug("%d Didactalia traces read." % len(traces))
        self._process_traces(traces)

    def dump_to_graph(self, graph: Graph) -> int:
        LOG.debug("Going to dump %d Didactalia traces into RDF" % len(self._activities))
        nb_total_triples = sum((a.dump_to_graph(graph) for a in self._activities))
        return nb_total_triples

    def _process_traces(self, traces):
        # Prepare the mapping actionType - process
        game_played_activities = dict()  # A buffer to store game_played activities by their playSession

        # Specific treatment wrappers
        def treat_play_start(tr):
            a = GamePlayedActivity(tr)
            game_played_activities[tr['playSession']] = a
            return a

        def treat_play_end(tr):
            if tr['playSession'] not in game_played_activities:
                LOG.warning("Trace playEnd of id %s happened wihtout any relative playStart. Cannot process it" % tr['_id'])
                return None
            else:
                return game_played_activities[tr['playSession']].end_activity(tr)

        def treat_game_attr_change(tr):
            if tr['playSession'] not in game_played_activities:
                LOG.warning("Trace %s of id %s happened without (t=%s) any relative playStart. "
                            "Process it without any superEvent"
                            % (tr['actionType'], tr['_id'], tr['date'].strftime('%d/%m/%Y %H:%M:%S %z')))
                return GameAttributeChanged(tr, None)
            else:
                return GameAttributeChanged(tr, game_played_activities[trace['playSession']])

        # Mapping actionType -> process (of a trace into an instance or None)
        action_type_mapper = defaultdict(lambda: (lambda x: None))
        action_type_mapper['resourceVisited'] = ArtifactView
        action_type_mapper['freeTextSearch'] = SearchActivity
        action_type_mapper['facetsSearchAdd'] = FacetAddActivity
        action_type_mapper['facetsSearchRemove'] = FacetRemoveActivity
        action_type_mapper['playStart'] = treat_play_start
        action_type_mapper['playEnd'] = treat_play_end
        action_type_mapper['answersDetailsStateChange'] = treat_game_attr_change
        action_type_mapper['playStudyChange'] = treat_game_attr_change
        action_type_mapper['labelStateChange'] = treat_game_attr_change
        action_type_mapper['languageChange'] = treat_game_attr_change
        action_type_mapper['audioStateChange'] = treat_game_attr_change

        for trace in traces:
            # Process the trace into a possible activity
            activity = action_type_mapper[trace['actionType']](trace)
            if activity is not None:
                self._activities.append(activity)

    @staticmethod
    def _process_raw_trace(rt, learners_parser: LearnerMappingParser):
        tr = rt['_source']
        tr['_id'] = rt['_id']
        tr['date'] = dateparser.parse(tr['date'])
        tr['user'] = learners_parser.get_user_by_userid(tr['user_id'])
        # Some of the traces do not have any actionType (error from didactalia), we use then the type field instead
        tr['actionType'] = tr['actionType'] if 'actionType' in tr else tr['type']
        return tr


if __name__ == '__main__':
    from ..common.utils import get_default_loggin_config
    get_default_loggin_config(logging.DEBUG)
    LOG.info("No test to do.")
