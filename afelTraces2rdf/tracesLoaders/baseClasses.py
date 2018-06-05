# -*- coding: utf-8 -*-
# Author: Rémi Venant
from abc import abstractmethod
from rdflib import Graph, Literal
from rdflib.namespace import RDF
from ..common.namespaces import AfelNamespacesManager, concatenate_uriref

__all__ = ['TracesParser', 'Questionnaire', 'Question', 'Answer', 'CommentAnswer', 'RatingAnswer',
           'IntRatingAnswer', 'FloatRatingAnswer']

class TracesParser:
    @abstractmethod
    def load(self, f, *args, **kwargs):
        pass

    @abstractmethod
    def dump_to_graph(self, graph: Graph, *args, **kwargs):
        pass


class Questionnaire:
    def __init__(self, id: str, name: str, comment: str):
        self.id = id
        self.name = name
        self.comment = comment

        extans = AfelNamespacesManager().ext_afel_ns
        self._rdf_questionnaire = concatenate_uriref(extans.Questionnaire, self.id)

    @property
    def rdf_questionnaire(self):
        return self._rdf_questionnaire

    def dump_to_graph(self, graph: Graph):
        extans = AfelNamespacesManager().ext_afel_ns
        schns = AfelNamespacesManager().schema_ns
        # Dump Learner triples
        graph.add((self._rdf_questionnaire, RDF.type, extans.Questionnaire))
        graph.add((self._rdf_questionnaire, schns.identifier, Literal(self.id)))
        graph.add((self._rdf_questionnaire, schns.name, Literal(self.name)))
        graph.add((self._rdf_questionnaire, schns.comment, Literal(self.comment)))


class Question:
    def __init__(self, id, text, questionnaire: Questionnaire):
        self.id = id
        self.text = text
        self.questionnaire = questionnaire

        schema = AfelNamespacesManager().schema_ns
        self._rdf_question = concatenate_uriref(schema.Question, self.questionnaire.id + '_' + self.id)

    @property
    def rdf_question(self):
        return self._rdf_question

    def dump_to_graph(self, graph: Graph):
        schema = AfelNamespacesManager().schema_ns
        graph.add((self._rdf_question, RDF.type, schema.Question))
        graph.add((self._rdf_question, schema.identifier, Literal(self.id)))
        graph.add((self._rdf_question, schema.text, Literal(self.text)))
        graph.add((self._rdf_question, schema.isPartOf, self.questionnaire.rdf_questionnaire))


class Answer:
    def __init__(self, userid, user_rdf, time, question:Question):
        self.userid = userid
        self.user_rdf = user_rdf
        self.question = question
        self.time = time
        self.id = self.question.id + "_" + self.userid

    @abstractmethod
    def dump_to_graph(self, graph: Graph):
        pass


class CommentAnswer(Answer):
    def __init__(self, userid, user_rdf, date, question:Question, text):
        super().__init__(userid, user_rdf, date, question)
        self.text = text
        self._complete_id = self.question.id + '_' + self.id

    def dump_to_graph(self, graph: Graph):
        schema = AfelNamespacesManager().schema_ns
        # Create Comment
        rdf_answer = concatenate_uriref(schema.Answer, self._complete_id)
        graph.add((rdf_answer, RDF.type, schema.Answer))
        graph.add((rdf_answer, schema.identifier, Literal(self._complete_id)))
        graph.add((rdf_answer, schema.text, Literal(self.text)))
        # Create CommentAction
        rdf_action = concatenate_uriref(schema.CommentAction, self._complete_id)
        graph.add((rdf_action, RDF.type, schema.CommentAction))
        graph.add((rdf_action, schema.identifier, Literal(self._complete_id)))
        graph.add((rdf_action, schema.startTime, Literal(self.time)))
        graph.add((rdf_action, schema.endTime, Literal(self.time)))
        # Link both comment and commentAction to user
        graph.add((rdf_answer, schema.author, self.user_rdf))
        graph.add((rdf_action, schema.agent, self.user_rdf))
        # Link CommentAction to Comment and CommentAction to Question
        graph.add((rdf_action, schema.resultComment, rdf_answer))
        graph.add((rdf_action, schema.object, self.question.rdf_question))


class RatingAnswer(Answer):
    def __init__(self, userid, user_rdf, date, question: Question, value):
        super().__init__(userid, user_rdf, date, question)
        self.value = value
        self._complete_id = self.question.id + '_' + self.id

    def dump_to_graph(self, graph: Graph):
        schema = AfelNamespacesManager().schema_ns
        # Create Comment
        rdf_answer = concatenate_uriref(schema.Rating, self._complete_id)
        graph.add((rdf_answer, RDF.type, schema.Rating))
        graph.add((rdf_answer, schema.identifier, Literal(self._complete_id)))
        graph.add((rdf_answer, schema.ratingValue, Literal(self.value)))
        # Create CommentAction
        rdf_action = concatenate_uriref(schema.ChooseAction, self._complete_id)
        graph.add((rdf_action, RDF.type, schema.ChooseAction))
        graph.add((rdf_action, schema.identifier, Literal(self._complete_id)))
        graph.add((rdf_action, schema.startTime, Literal(self.time)))
        graph.add((rdf_action, schema.endTime, Literal(self.time)))
        # Link both comment and commentAction to user
        graph.add((rdf_answer, schema.author, self.user_rdf))
        graph.add((rdf_action, schema.agent, self.user_rdf))
        # Link CommentAction to Comment and CommentAction to Question
        graph.add((rdf_action, schema.actionOption, rdf_answer))
        graph.add((rdf_action, schema.object, self.question.rdf_question))


class IntRatingAnswer(RatingAnswer):
    def __init__(self, userid, user_rdf, date, question: Question, value):
        try:
            super().__init__(userid, user_rdf, date, question, int(float(value)))
        except:
            print("value on error: %s" % value)
            raise


class FloatRatingAnswer(RatingAnswer):
    def __init__(self, userid, user_rdf, date, question: Question, value):
        super().__init__(userid, user_rdf, date, question, float(value))