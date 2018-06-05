# -*- coding: utf-8 -*-
# author: Rémi Venant
import csv
import os
import re
import logging
from rdflib import Graph
import dateutil.parser as dateparser
from .baseClasses import Questionnaire, Question, CommentAnswer, IntRatingAnswer, FloatRatingAnswer

__all__ = ['KnwoledgesQuestionairesParser', 'KnowledgeQuestionnaireParser']

LOG = logging.getLogger(__name__)


class KnwoledgesQuestionairesParser:
    FILE_INFO_MAPPING = {
        'calib_geo.csv': ('AFEL_2_KNOW_PRE_GEO', 'Pre-test in geography',
                          'Pre-test questionnaire on geographical knowledge used for the 2nd AFEL evaluation'),
        'calib_geo.csv': ('AFEL_2_KNOW_PRE_HIST', 'Pre-test in history',
                          'Pre-test questionnaire on historical knowledge used for the 2nd AFEL evaluation'),
        'final_geo.csv': ('AFEL_2_KNOW_POST_GEO', 'Post-test in geography',
                          'Post-test questionnaire on geographical knowledge used for the 2nd AFEL evaluation'),
        'final_geo.csv': ('AFEL_2_KNOW_POST_HIST', 'Post-test in history',
                          'Post-test questionnaire on historical knowledge used for the 2nd AFEL evaluation'),

    }

    def __init__(self):
        pass

    def load_and_dump(self, base_directory, learners_parser, graph: Graph, dialect: str='unix'):
        for filename, info in self.FILE_INFO_MAPPING.items():
            LOG.info("Process %s..." % info[1])
            parser = KnowledgeQuestionnaireParser(info[0], info[1], info[2])
            with open(os.path.join(base_directory, filename), 'r') as f_in:
                parser.load_and_dump(f_in, learners_parser, graph, dialect=dialect)
            LOG.info("Process of %s done." % info[1])


class KnowledgeQuestionnaireParser:
    def __init__(self, quest_id, quest_name, quest_comment):
        self.quest_id = quest_id
        self.quest_name = quest_name
        self.quest_comment = quest_comment

    @property
    def questionnaire(self):
        return self._questionaire

    def load_and_dump(self, f, learners_parser, graph: Graph, dialect: str='unix'):
        # Create and dump the questionnaire
        self._create_rdf_questionnaire().dump_to_graph(graph)
        # Read the header to extract the questions
        csv_reader = csv.reader(f, dialect=dialect)
        questions = self._create_questions(next(csv_reader)[1:-2])
        # dump the questions
        for q in questions:
            q.dump_to_graph(graph)

        # For each line, get user and parse answer
        for row in csv_reader:
            userid, user = self._extract_user(row[0], learners_parser)
            answers = self._parse_answers(row[1:], userid, user, questions)
            # dump answers
            for answer in answers:
                answer.dump_to_graph(graph)

    def _create_rdf_questionnaire(self):
        self._questionaire = Questionnaire(self.quest_id, self.quest_name, self.quest_comment)
        return self._questionaire

    def _create_questions(self, questions_ids):
        return [Question(qid, qid, self._questionaire) for qid in questions_ids]

    @staticmethod
    def _extract_user(id, learners_parser):
        if '@' in id:
            r = re.compile('(\d+)@')
            id = r.findall('project.afel046@gmail.com')[0]
            return id, learners_parser.get_user_by_email_id(id)
        else:
            return id, learners_parser.get_user_by_email_id(id)

    def _parse_answers(self, answers, userid, user, questions):
        # all the answer are lickert from 1 to 5 execpt for the last 2 ones
        # last-1 answer is the time, last is the ip
        date = dateparser.parse(answers[-2])
        return [IntRatingAnswer(userid, user, date, questions[i], val) for i, val in enumerate(answers[:-2])]



