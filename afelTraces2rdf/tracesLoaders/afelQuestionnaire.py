# -*- coding: utf-8 -*-
# author: Rémi Venant
import logging
import csv
import ujson as json
import datetime
from rdflib import Graph
from .baseClasses import Questionnaire, Question, CommentAnswer, IntRatingAnswer, FloatRatingAnswer

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


    def _create_dump_questionnaire(self, graph: Graph):
        questionaire = Questionnaire(self.questionnaire_id, self.questionnaire_name, self.questionnaire_comment)
        questionaire.dump_to_graph(graph)
        return questionaire

    @staticmethod
    def _create_dump_questions_from_headers(headers, details, questionnaire, graph: Graph):
        questions = [Question(qid, details[qid], questionnaire) for qid in headers[1:]]
        for q in questions:
            q.dump_to_graph(graph)
        return questions

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

    def load_and_dump(self, f_details, f_data, rdf_user_finder, graph: Graph, dialect='unix', *args, **kwargs):
        # Load details
        LOG.debug("Load details")
        details = json.load(f_details)
        # Load data
        LOG.debug("Load questionnaire data")
        csv_reader = csv.reader(f_data, dialect=dialect)
        # Extract headers containing questions' ids
        headers = next(csv_reader) # Asumption : first header is ID
        # Create questionaire and dump it
        LOG.debug("Create questionnaire")
        questionnaire = self._create_dump_questionnaire(graph)
        # Create questions and dump them
        LOG.debug("Load questions")
        questions = self._create_dump_questions_from_headers(headers, details, questionnaire, graph)
        # set a common date for all action as it is not given in data
        date = datetime.datetime(year=2018, month=5, day=23, hour=10)
        # Process answers
        nb_users = 0
        nb_answers = 0
        LOG.debug("Process answers")
        # prepare answer forge
        answer_forge = self._compute_answer_forge()
        for row in csv_reader:
            # get userids (may have several
            for userid in [uid.strip() for uid in row[0].split('&')]:
                rdf_user = rdf_user_finder(userid)
                answers = [answer_forge[i](userid, rdf_user, date, questions[i], a) for i, a in enumerate(row[1:])
                           if a is not None and a]
                for answer in answers:
                    answer.dump_to_graph(graph)
                    nb_answers += 1
                nb_users += 1
        LOG.debug("%d answerers processed, %d questions processed" % (nb_users, nb_answers))
