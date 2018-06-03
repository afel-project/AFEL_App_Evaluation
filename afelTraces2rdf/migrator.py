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
from .common.utils import get_default_loggin_config

LOG = logging.getLogger(__name__)

# NamedTuple structure used to manipulate files or parsers collection
COLLECTIONS_NAME = ['learners', 'didactalia', 'afelApp']
TracesCollection = namedtuple('TracesCollection', COLLECTIONS_NAME)


def check_files_locations(files_collection: TracesCollection):
    """
    Check that all filenames has been given and exist. Raise an assertException otherwise.
    :param files_collection: the collection of filenames
    :return: the files collection
    """
    assert all((loc is None or os.path.isfile(loc) for loc in files_collection))
    assert files_collection.learners is not None
    return files_collection


def process_traces(files_collection: TracesCollection, **kwargs):
    """
    Create parser for each traces collection and parse & convert all traces
    :param files_collection: the traces files collection
    :param kwargs: extra arg, especially 'dialect' and 'has_header' for the csv parser (learners)
    :return: the parsers collection as a TracesCollection namedtuple
    """

    graph = Graph()

    LOG.info("Parse learners...")
    learners_parser = LearnerMappingParser()
    with open(files_collection.learners, 'r') as f:
        learners_parser.load(f)
    LOG.info("Convert learners...")
    learners_parser.dump_to_graph(graph)
    LOG.info("Process learners done.")

    if files_collection.didactalia is not None:
        LOG.info("Parse Didactalia traces...")
        parser = DidactaliaLearningTracesParser()
        with open(files_collection.didactalia, 'rb') as f:
            parser.load(f, lambda x: learners_parser.get_user(x))
        LOG.info("Convert Didactalia traces into RDF...")
        parser.dump_to_graph(graph)
        LOG.info("Process Didactalia traces done.")

    if files_collection.afelApp is not None:
        LOG.info("Process Afel App traces...")
        parser = AfelAppTracesParser()
        with open(files_collection.afelApp, 'rb') as f:
            parser.load(f, lambda x: learners_parser.get_user(x))
        LOG.info("Convert Afel App traces into RDF...")
        parser.dump_to_graph(graph)
        LOG.info("Process Afel App done.")

    return graph


def save_graph_to_file(graph:Graph, destination: str, format:str='pretty-xml', **kwargs):
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
    # parser.add_argument('-aq', '--afelapp-questionaire', help='user mail - Userid mapping file', type=str,
    #                    default='resources/raw_traces/userID_mapping.csv')
    # parser.add_argument('-kq', '--knwoledge-questionaire', help='user mail - Userid mapping file', type=str,
    #                    default='resources/raw_traces/userID_mapping.csv')

    return parser.parse_args()


def main():
    get_default_loggin_config(logging.INFO)
    args = configure_args()

    #Init namespace manager with the different given arguments
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
                 afelApp=args.afelapp_traces)

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