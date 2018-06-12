# -*- coding: utf-8 -*-
# author: Rémi Venant
import logging
import csv
import ujson as json
import datetime
import pytz
from rdflib import Graph
from .baseClasses import Questionnaire, Question, CommentAnswer, IntRatingAnswer, FloatRatingAnswer
from .learners import LearnerMappingParser

__all__ = ['AfelQuestionnaireParser']

LOG = logging.getLogger(__name__)


class AfelQuestionnaireParser:
    """
    The parser to load a csv file of email-id and create RDF triples to represent the learners and their user account
    """
    def __init__(self):
        self.questionnaire_id = 'AFEL_QUEST_APP_2'
        self.questionnaire_name = "2nd AFEL evaluation App questionaire"
        self.questionnaire_comment = "A questionaire to evaluate the quality of the AFEL App"

    def load_and_dump(self, f_details, f_data, learners_parser: LearnerMappingParser,
                      graph: Graph, dialect='unix') -> int:
        nb_triples = 0
        # Load details
        LOG.debug("Load details")
        details = json.load(f_details)
        # Load data
        LOG.debug("Load questionnaire data")
        csv_reader = csv.reader(f_data, dialect=dialect)
        # Extract headers containing questions' ids
        headers = next(csv_reader)  # Asumption : first header is ID
        # Create questionaire and dump it
        LOG.debug("Create questionnaire")
        questionnaire = Questionnaire(self.questionnaire_id, self.questionnaire_name, self.questionnaire_comment)
        nb_triples += questionnaire.dump_to_graph(graph)
        # Create questions and dump them
        LOG.debug("Load questions")
        questions = [Question(qid, details[qid], questionnaire) for qid in headers[1:]]
        nb_triples += sum((q.dump_to_graph(graph) for q in questions))
        # set a common date for all action as it is not given in data
        date = datetime.datetime(year=2018, month=5, day=20, tzinfo=pytz.utc)
        # Process answers
        nb_users = 0
        nb_answers = 0
        LOG.debug("Process answers")
        # prepare answer forge
        answer_forge = self._compute_answer_forge()
        for row in csv_reader:
            # get userids (may have several
            for userid in [int(uid.strip()) for uid in row[0].split('&')]:
                user = learners_parser.get_user_by_internalid(userid)
                answers = [answer_forge[i](user, date, questions[i], a) for i, a in enumerate(row[1:])
                           if a is not None and a]
                nb_triples += sum((a.dump_to_graph(graph) for a in answers))
                nb_answers += len(answers)
                nb_users += 1
        LOG.debug("%d users processed, %d answers processed" % (nb_users, nb_answers))
        return nb_triples

    @staticmethod
    def _compute_answer_forge():
        answer_forge = [IntRatingAnswer] * 27 \
                       + [CommentAnswer] * 2 \
                       + [IntRatingAnswer] * 5 \
                       + [CommentAnswer] \
                       + [IntRatingAnswer] * 3 \
                       + [CommentAnswer] * 2 \
                       + [FloatRatingAnswer] * 6
        return answer_forge
