# -*- coding: utf-8 -*-
# author: Rémi Venant
import csv
import os
import re
import logging
from rdflib import Graph
import pytz
import dateutil.parser as dateparser
from .baseClasses import Questionnaire, Question, IntRatingAnswer, User
from .learners import LearnerMappingParser

__all__ = ['KnowledgeQuestionairesParser']

LOG = logging.getLogger(__name__)


class KnowledgeQuestionairesParser:
    FILE_INFO_MAPPING = {
        'calib_geo_corrected.csv': ('AFEL_2_KNOW_PRE_GEO', 'Pre-test in geography',
                          'Pre-test questionnaire on geographical knowledge used for the 2nd AFEL evaluation'),
        'calib_hist_corrected.csv': ('AFEL_2_KNOW_PRE_HIST', 'Pre-test in history',
                           'Pre-test questionnaire on historical knowledge used for the 2nd AFEL evaluation'),
        'final_geo_corrected.csv': ('AFEL_2_KNOW_POST_GEO', 'Post-test in geography',
                          'Post-test questionnaire on geographical knowledge used for the 2nd AFEL evaluation'),
        'final_hist_corrected.csv': ('AFEL_2_KNOW_POST_HIST', 'Post-test in history',
                           'Post-test questionnaire on historical knowledge used for the 2nd AFEL evaluation'),
        'nfa_geo_corrected.csv': ('AFEL_2_META_AFFECT_GEO', 'Need for affect questionnaire in geography',
                        'Meta-cognition test before the pre-test questionnaire to measure the '
                        'need for affect in geography'),
        'nfa_hist_corrected.csv': ('AFEL_2_META_AFFECT_HIST', 'Need for affect questionnaire in history',
                         'Meta-cognition test before the pre-test questionnaire to measure the '
                         'need for affect in history'),
        'nfc_geo_corrected.csv': ('AFEL_2_META_COG_GEO', 'Need for cognition questionnaire in geography',
                        'Meta-cognition test before the pre-test questionnaire to measure the '
                        'need for cognition in geography'),
        'nfc_hist_corrected.csv': ('AFEL_2_META_COG_HIST', 'Need for cognition questionnaire in history',
                         'Meta-cognition test before the pre-test questionnaire to measure the '
                         'need for cognition in history')
    }

    def __init__(self):
        pass

    def load_and_dump(self, base_directory, learners_parser, graph: Graph, dialect: str = 'unix') -> int:
        total_nb_triples = 0
        for filename, info in self.FILE_INFO_MAPPING.items():
            LOG.info("Process %s..." % info[1])
            parser = KnowledgeQuestionnaireParser(info[0], info[1], info[2])
            with open(os.path.join(base_directory, filename), 'r') as f_in:
                total_nb_triples += parser.load_and_dump(f_in, learners_parser, graph, dialect=dialect)
            LOG.info("Process of %s done." % info[1])
        return total_nb_triples


class KnowledgeQuestionnaireParser:
    _TIMEZONE = pytz.timezone('Europe/Madrid')

    def __init__(self, quest_id, quest_name, quest_comment):
        self.quest_id = quest_id
        self.quest_name = quest_name
        self.quest_comment = quest_comment

        self._questionnaire = Questionnaire(self.quest_id, self.quest_name, self.quest_comment)

    @property
    def questionnaire(self):
        return self._questionnaire

    def load_and_dump(self, f, learners_parser: LearnerMappingParser, graph: Graph, dialect: str = 'unix') -> int:
        total_nb_triples = 0
        # Dump the questionnaire
        total_nb_triples += self.questionnaire.dump_to_graph(graph)

        # Read the header to extract the questions
        csv_reader = csv.reader(f, dialect=dialect)
        questions_ids = next(csv_reader)[1:-2]
        questions = [Question(qid=qid, text=qid, questionnaire=self._questionnaire) for qid in questions_ids]
        LOG.debug("nb questions: %d" % len(questions))
        # dump the questions
        total_nb_triples += sum((q.dump_to_graph(graph) for q in questions))

        # Parse csv
        nb_users = 0
        nb_answers = 0
        for row in csv_reader:
            # Get user and answers
            try:
                user = self._extract_user(row[0], learners_parser)
            except (ValueError, KeyError):
                LOG.warning("User %s unknown. Skip it." % row[0])
                continue
            answers = self._parse_answers(row[1:], user, questions)
            # dump answers
            total_nb_triples += sum((a.dump_to_graph(graph) for a in answers))
            nb_answers += len(answers)
            # LOG.debug("nb answer for userid %s: %d" % (user.userid, len(answers)))
            nb_users += 1
        LOG.debug("Nb rows: %d, Nb_answers: %d" % (nb_users, nb_answers))
        LOG.debug("%d triples should have been writen" % total_nb_triples)
        return total_nb_triples

    @staticmethod
    def _extract_user(uid, learners_parser) -> User:
        if '@' in uid:
            uid = int(re.compile('(\d+)@').findall(uid)[0])
        else:
            uid = int(uid)
        return learners_parser.get_user_by_internalid(uid)

    @classmethod
    def _parse_answers(cls, answers, user: User, questions):
        # all the answer are lickert from 1 to 5 execpt for the last 2 ones
        # last-1 answer is the time, last is the ip
        date = cls._TIMEZONE.localize(dateparser.parse(answers[-2])).astimezone(pytz.utc)
        return [IntRatingAnswer(user, date, questions[i], val) for i, val in enumerate(answers[:-2])]
