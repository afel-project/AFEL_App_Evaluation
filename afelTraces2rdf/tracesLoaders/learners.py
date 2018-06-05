# -*- coding: utf-8 -*-
# author: Rémi Venant
import logging
import warnings
import csv
from rdflib.namespace import RDF
from rdflib import Literal, Graph
from .baseClasses import TracesParser
from ..common.namespaces import AfelNamespacesManager, concatenate_uriref

__all__ = ['LearnerMappingParser', 'Learner']

LOG = logging.getLogger(__name__)


class Learner:
    '''
    Learner represent a learner stored in the email-userid mapping file
    '''
    def __init__(self, email: str, userid: str):
        self.email = email
        self.username = self.firstname = email.split('@')[0]
        self.userid = userid if userid else self.username
        self.lastname = "Afel" # We use a arbitrary fullname as users are all experiment users
        self.__init_rdf_instances()

    def __init_rdf_instances(self):
        ans = AfelNamespacesManager().afel_ns
        self.rdf_learner = concatenate_uriref(ans.Learner, self.username)
        self.rdf_user = concatenate_uriref(ans.User, self.username)

    def dump_to_graph(self, graph: Graph):
        ans = AfelNamespacesManager().afel_ns
        # Dump Learner triples
        graph.add((self.rdf_learner, RDF.type, ans.Learner))
        graph.add((self.rdf_learner, ans.email, Literal(self.email)))
        graph.add((self.rdf_learner, ans.firstName, Literal(self.firstname)))
        graph.add((self.rdf_learner, ans.lastName, Literal(self.lastname)))
        graph.add((self.rdf_learner, ans.id, Literal(self.userid)))
        # Dump User triples
        graph.add((self.rdf_user, RDF.type, ans.User))
        graph.add((self.rdf_user, ans.person, self.rdf_learner))
        graph.add((self.rdf_user, ans.userID, Literal(self.userid)))
        graph.add((self.rdf_user, ans.userName, Literal(self.username)))


class LearnerMappingParser(TracesParser):
    """
    The parser to load a csv file of email-id and create RDF triples to represent the learners and their user account
    """
    def __init__(self):
        self._learners_by_userid = dict()

    def load(self, f, dialect='unix', has_header=True, *args, **kwargs):
        csv_reader = csv.reader(f, dialect=dialect)
        if has_header:
            # Skip and check the header if any
            headers = next(csv_reader)
            if len(headers) != 2 or headers[0].lower() != "login" or headers[1].lower() != "userid":
                raise Exception("Csv must be 2-columns: login (email), userid")
        # Parse csv rows
        self._learners_by_userid = dict()
        nb_read = 0
        for row in csv_reader:
            if not row[0]:
                LOG.warning("Incomplete learner email. : email='%s', userid='%s'. Skipping it." % (row[0], row[1]))
                continue
            l = Learner(row[0], row[1])
            self._learners_by_userid[l.userid] = l
            nb_read += 1
        LOG.debug("%d learners read." % nb_read)

    def has_learner(self, userid: str):
        return userid in self._learners_by_userid

    def get_learner(self, userid: str):
        return self._learners_by_userid[userid].rdf_learner

    def has_user(self, userid: str):
        return userid in self._learners_by_userid

    def get_user(self, userid: str):
        return self._learners_by_userid[userid].rdf_user

    def get_user_by_email(self, email: str):
        return list(filter(lambda x:x.email == email, self._learners_by_userid.values()))[0].rdf_user

    def get_user_by_email_id(self, email_id: str):
        email = "project.afel+%03d@gmail.com" % int(email_id)
        return self.get_user_by_email(email)

    def dump_to_graph(self, graph: Graph, *args, **kwargs):
        LOG.debug("Going to dump %d learners into RDF" % len(self._learners_by_userid))
        for learner in self._learners_by_userid.values():
            learner.dump_to_graph(graph)


if __name__ == '__main__':
    from ..common.utils import get_default_loggin_config
    import sys
    get_default_loggin_config(logging.DEBUG)
    if len(sys.argv) != 3:
        LOG.error("Cannot test learner parser, please give the learner mapping file and the rdf out file in parameter.")
        sys.exit(1)
    LOG.info("Test Learner parser")
    parser = LearnerMappingParser()
    LOG.debug("start loading")
    with open(sys.argv[1], 'r') as f:
        parser.load(f)
    LOG.debug("Dump data into an RDF Graph")
    g = Graph()
    parser.dump_to_graph(g)
    LOG.debug("Print result")
    res = g.serialize(destination=sys.argv[2], format='pretty-xml')
    print(res)
    LOG.info("Test done properly.")

