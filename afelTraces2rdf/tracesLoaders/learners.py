# -*- coding: utf-8 -*-
# author: Rémi Venant
import logging
import re
import csv
from rdflib.namespace import RDF
from rdflib import Literal, Graph, URIRef
from .baseClasses import Person, User
from ..common.namespaces import AfelNamespacesManager, concatenate_uriref

__all__ = ['LearnerMappingParser', 'AFELLearner']

LOG = logging.getLogger(__name__)


class AFELLearner(Person):
    def __init__(self, email: str, userid: str):
        self.email = email
        self.username = self.firstname = email.split('@')[0]
        self.lastname = "Afel"
        self.userid = userid if userid else self.username
        self.internalid = int(re.compile('(\d+)$').findall(self.username)[0])
        self._init_user()

    def _init_user(self):
        self._user = User(self.userid, self.username, self)

    @property
    def rdf(self) -> URIRef:
        ans = AfelNamespacesManager().afel_ns
        return concatenate_uriref(ans.Learner, self.username)

    @property
    def user(self) -> User:
        return self._user

    def dump_to_graph(self, graph: Graph) -> int:
        ans = AfelNamespacesManager().afel_ns
        # Dump Learner triples
        rdf = self.rdf
        graph.add((rdf, RDF.type, ans.Learner))
        graph.add((rdf, ans.email, Literal(self.email)))
        graph.add((rdf, ans.firstName, Literal(self.firstname)))
        graph.add((rdf, ans.lastName, Literal(self.lastname)))
        graph.add((rdf, ans.id, Literal(self.userid)))
        nb_triples = 5 + self._user.dump_to_graph(graph)
        return nb_triples


class LearnerMappingParser:
    """
    The parser to load a csv file of email-id and create RDF triples to represent the learners and their user account
    """
    def __init__(self):
        self._learners_by_userid = dict()
        self._learners_by_internalid = dict()

    def load_and_dump(self, fin, graph: Graph, dialect='unix', has_header=True, *args, **kwargs):
        csv_reader = csv.reader(fin, dialect=dialect)
        if has_header:
            # Skip and check the header if any
            headers = next(csv_reader)
            if len(headers) != 2 or headers[0].lower() != "login" or headers[1].lower() != "userid":
                raise Exception("Csv must be 2-columns: login (email), userid")
        # Parse csv rows and build learners
        self._learners_by_userid = dict()
        self._learners_by_internalid = dict()
        nb_read = 0
        for row in csv_reader:
            if not row[0]:
                LOG.warning("Incomplete learner email. : email='%s', userid='%s'. Skipping it." % (row[0], row[1]))
                continue
            learner = AFELLearner(row[0], row[1])
            self._learners_by_userid[learner.userid] = learner
            self._learners_by_internalid[learner.internalid] = learner
            nb_read += 1
        LOG.debug("%d learners read." % nb_read)
        # dump learners to graph
        LOG.debug("Going to dump %d learners into RDF" % len(self._learners_by_userid))
        nb_triples = 0
        for learner in self._learners_by_userid.values():
            nb_triples += learner.dump_to_graph(graph)
        LOG.debug("%d triples should have been writen" % nb_triples)
        return nb_triples

    def get_user_by_internalid(self, internalid: int) -> AFELLearner:
        return self._learners_by_internalid[internalid].user

    def get_user_by_userid(self, userid: str) -> AFELLearner:
        return self._learners_by_userid[userid].user

    '''
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
        
        for learner in self._learners_by_userid.values():
            learner.dump_to_graph(graph)
    '''


def _test():
    from ..common.utils import get_default_loggin_config
    import sys
    get_default_loggin_config(logging.DEBUG)
    if len(sys.argv) != 3:
        LOG.error("Cannot test learner parser, please give the learner mapping file and the rdf out file in parameter.")
        sys.exit(1)
    LOG.info("Test Learner parser")
    parser = LearnerMappingParser()
    LOG.debug("start loading")
    g = Graph()
    with open(sys.argv[1], 'r') as f:
        parser.load_and_dump(f, g)
    LOG.debug("Print result")
    res = g.serialize(destination=sys.argv[2], format='pretty-xml')
    print(res)
    LOG.info("Test done properly.")


if __name__ == '__main__':
    _test()
