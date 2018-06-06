# -*- coding: utf-8 -*-
import os
import sys
import warnings
import logging
import argparse
from collections import namedtuple
from rdflib import Graph
from .common.namespaces import AfelNamespacesManager
from .tracesLoaders.learners import LearnerMappingParser
from .tracesLoaders.afelAppTraces import AfelAppTracesParser
from .tracesLoaders.didactaliaTraces import DidactaliaLearningTracesParser
from .tracesLoaders.afelQuestionnaire import AfelQuestionnaireParser
from .tracesLoaders.knowledgeQuestionnaires import KnowledgeQuestionairesParser
from .common.utils import get_default_loggin_config

LOG = logging.getLogger(__name__)

# NamedTuple structure used to manipulate files or parsers collection
COLLECTIONS_NAME = ['learners', 'didactalia', 'afelApp', 'appQuest', 'appQuestDetails', 'knowledge']
TracesCollection = namedtuple('TracesCollection', COLLECTIONS_NAME)


class GraphDuplicateWatcher(Graph):
    __NORMAL_PREFIXES = ["http://vocab.afel-project.eu/Artifact",]

    def __init__(self, *largs, **kwargs):
        super().__init__(*largs, **kwargs)
        self.__duplicate_checker = set()
        self.__duplicates_count = 0

    def add(self, triple):
        hash_key = "_".join((p for p in triple))
        if hash_key in self.__duplicate_checker:
            if not self.__is_duplicates_normal(triple):
                LOG.warning("DUPLICATE FOUND: %s %s %s" % triple)
            self.__duplicates_count += 1
        else:
            self.__duplicate_checker.add(hash_key)
        super().add(triple)

    @classmethod
    def __is_duplicates_normal(cls, triple):
        return any((triple[0].startswith(pr) for pr in cls.__NORMAL_PREFIXES))

    @property
    def duplicates_count(self):
        return self.__duplicates_count


def check_files_locations(files_collection: TracesCollection):
    """
    Check that all filenames has been given and exist. Raise an assertException otherwise.
    :param files_collection: the collection of filenames
    :return: the files collection
    """
    assert all((loc is None or os.path.exists(loc) for loc in files_collection))
    assert files_collection.learners is not None
    return files_collection


def process_traces(files_collection: TracesCollection):
    """
    Create parser for each traces collection and parse & convert all traces
    :param files_collection: the traces files collection
    :return: the parsers collection as a TracesCollection namedtuple
    """

    graph = GraphDuplicateWatcher()  # TODO : Replace with classic Graph()
    total_nb_triples = 0

    LOG.info("Process learners...")
    learners_parser = LearnerMappingParser()
    with open(files_collection.learners, 'r') as f:
        total_nb_triples += learners_parser.load_and_dump(f, graph)
    LOG.info("Process learners done.")

    if files_collection.didactalia is not None:
        LOG.info("Process Didactalia traces...")
        parser = DidactaliaLearningTracesParser()
        with open(files_collection.didactalia, 'rb') as f:
            total_nb_triples += parser.load_and_dump(f, learners_parser, graph)
        LOG.info("Process Didactalia traces done.")

    if files_collection.afelApp is not None:
        LOG.info("Process Afel App traces...")
        parser = AfelAppTracesParser()
        with open(files_collection.afelApp, 'rb') as f:
            total_nb_triples += parser.load_and_dump(f, learners_parser, graph)
        LOG.info("Process Afel App done.")

    if files_collection.appQuest is not None:
        LOG.info("Process Afel App Questionaire traces...")
        parser = AfelQuestionnaireParser()
        with open(files_collection.appQuest, 'r') as f_data, open(files_collection.appQuestDetails, 'rb') as f_details:
            total_nb_triples += parser.load_and_dump(f_details, f_data, learners_parser, graph)
        LOG.info("Process Afel App Questionnaire done.")

    if files_collection.knowledge is not None:
        LOG.info("Process knowledge questionnaires...")
        parser = KnowledgeQuestionairesParser()
        total_nb_triples += parser.load_and_dump(files_collection.knowledge, learners_parser, graph)
        LOG.info("Process knowledge questionnaires done.")

    LOG.info("%d triples have been generated." % total_nb_triples)
    LOG.info("%d triples are duplicates" % graph.duplicates_count)
    LOG.info("%d triples should have been written" % (total_nb_triples - graph.duplicates_count))
    return graph


def save_graph_to_file(graph:Graph, destination: str, format: str='pretty-xml', **kwargs):
    """
    Save an RDF into a file
    :param graph: the RDF Graph
    :param destination: the destination (can be a file or a filename)
    :param format: the RDF format (‘xml’, ‘n3’, ‘turtle’, ‘nt’, ‘pretty-xml’, ‘trix’, ‘trig’ and ‘nquads’)
    :param kwargs: extra params such as base and enconding
    :return: the graph
    """
    graph.serialize(destination, format, **kwargs)
    return graph


def configure_args():
    parser = argparse.ArgumentParser(description="Convert Didactalia logs, AFEL App logs, "
                                                 "AFEL App Questionnaire and Knowledge "
                                                 "questionnaire into a single RDF file")

    parser.add_argument('destination', help='Output RDF file', type=str)
    parser.add_argument('-ff', '--file-format', help="RDF File format (among 'xml', 'n3', 'turtle', 'nt', "
                                                     "'pretty-xml', 'trix', 'trig' and 'nquads'), "
                                                     "only used if destination is a file", type=str, default='turtle')

    parser.add_argument('-ap', '--afel-publicid', help='Afel schema public id', type=str,
                        default='http://vocab.afel-project.eu/')
    parser.add_argument('-as', '--afel-schema', help='Afel schema source', type=str,
                        default='http://data.afel-project.eu/vocab/afel_schema.rdf')
    parser.add_argument('-eap', '--ext-afel-publicid', help='Extended Afel schema public id', type=str,
                        default='http://vocab.afel-project.eu/extension/')
    parser.add_argument('-eas', '--ext-afel-schema', help='Extended Afel schema source', type=str,
                        default='./resources/afel_schema_extension.rdf')

    parser.add_argument('-um', '--user-mapping', help='user mail - Userid mapping csv file', type=str,
                        default='resources/raw_traces/userID_mapping.csv')
    parser.add_argument('-dt', '--didactalia-traces', help='Didactalia traces json file', type=str,
                        default='resources/raw_traces/didactalia_activity/behaviour_traces.json')
    parser.add_argument('-at', '--afelapp-traces', help='AFEL App traces json file', type=str,
                        default='resources/raw_traces/app_logs/app_logs.json')
    parser.add_argument('-aq', '--afelapp-questionaire', help='AFEL App questionaire', type=str,
                        default='resources/raw_traces/app_questionnaire/app_questionnaire.csv')
    parser.add_argument('-aqd', '--afelapp-quest-details', help='AFEL App questionaire detail', type=str,
                        default='resources/raw_traces/app_questionnaire/question_details.json')
    parser.add_argument('-kq', '--knowledge-directory', help='Knowledge questionnaire directory', type=str,
                        default='resources/raw_traces/knowledge_questionnaire')

    return parser.parse_args()


def main():
    get_default_loggin_config(logging.INFO)
    args = configure_args()

    # Init namespace manager with the different given arguments
    try:
        AfelNamespacesManager(afel_source=args.afel_schema,
                              afel_publicID=args.afel_publicid,
                              ext_afel_source=args.ext_afel_schema,
                              ext_afel_publicID=args.ext_afel_publicid)
    except Exception as e:
        print("Namespace given cannot be treated. Please check you AFEL schema, publicid and EXT-AFEL schema, public.")
        print("Details: %s" % str(e))
        sys.exit(1)

    # Build traces files collections
    files_collec = TracesCollection(learners=args.user_mapping,
                                    didactalia=args.didactalia_traces,
                                    afelApp=args.afelapp_traces,
                                    appQuest=args.afelapp_questionaire,
                                    appQuestDetails=args.afelapp_quest_details,
                                    knowledge=args.knowledge_directory)

    # Assert that all file exists
    try:
        check_files_locations(files_collec)
    except Exception as e:
        print("One or several traces files given do not exist.")
        print("Details: %s" % str(e))
        sys.exit(1)

    with warnings.catch_warnings():
        warnings.simplefilter("default")

        # Start process
        LOG.info("Start processing traces files...")
        graph = process_traces(files_collec)
        LOG.info("Processing traces files done.")

        LOG.info("Saving into file...")
        save_graph_to_file(graph, destination=args.destination, format=args.file_format)
        LOG.info("Saving done.")

    print("Bye bye.")
    sys.exit(0)


if __name__ == '__main__':
    main()
