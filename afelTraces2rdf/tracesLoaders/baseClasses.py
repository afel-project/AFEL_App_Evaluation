# -*- coding: utf-8 -*-
# Author: Rémi Venant
from abc import abstractmethod, ABCMeta
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF
from ..common.namespaces import AfelNamespacesManager, concatenate_uriref

__all__ = ['RdfRepresentation', 'Person', 'User', 'Questionnaire', 'Question', 'Answer', 'CommentAnswer',
           'RatingAnswer', 'IntRatingAnswer', 'FloatRatingAnswer']


class RdfRepresentation(metaclass=ABCMeta):

    @abstractmethod
    def rdf(self) -> URIRef:
        pass

    @abstractmethod
    def dump_to_graph(self, graph: Graph) -> int:
        pass


class Person(RdfRepresentation, metaclass=ABCMeta):
    pass


class User(RdfRepresentation):
    def __init__(self, userid, username, person: Person=None):
        self.userid = userid
        self.username = username
        self.person = person

    @property
    def rdf(self) -> URIRef:
        ans = AfelNamespacesManager().afel_ns
        return concatenate_uriref(ans.User, self.username)

    def dump_to_graph(self, graph: Graph) -> int:
        ans = AfelNamespacesManager().afel_ns
        rdf_rep = self.rdf
        graph.add((rdf_rep, RDF.type, ans.User))
        graph.add((rdf_rep, ans.userID, Literal(self.userid)))
        graph.add((rdf_rep, ans.userName, Literal(self.username)))
        if self.person is not None:
            graph.add((rdf_rep, ans.person, self.person.rdf))

        return 4 if self.person is not None else 3


class Questionnaire(RdfRepresentation):
    def __init__(self, qid: str, name: str, comment: str):
        self.id = qid
        self.name = name
        self.comment = comment

    @property
    def rdf(self) -> URIRef:
        extans = AfelNamespacesManager().ext_afel_ns
        return concatenate_uriref(extans.Questionnaire, self.id)

    def dump_to_graph(self, graph: Graph) -> int:
        extans = AfelNamespacesManager().ext_afel_ns
        schns = AfelNamespacesManager().schema_ns
        # Dump Learner triples
        rdf = self.rdf
        graph.add((rdf, RDF.type, extans.Questionnaire))
        graph.add((rdf, schns.identifier, Literal(self.id)))
        graph.add((rdf, schns.name, Literal(self.name)))
        graph.add((rdf, schns.comment, Literal(self.comment)))

        return 4


class Question(RdfRepresentation):
    def __init__(self, qid, text, questionnaire: Questionnaire):
        self.id = qid
        self.fullid = questionnaire.id + '_' + qid
        self.text = text
        self.questionnaire = questionnaire

    @property
    def rdf(self) -> URIRef:
        schema = AfelNamespacesManager().schema_ns
        return concatenate_uriref(schema.Question, self.fullid)

    def dump_to_graph(self, graph: Graph) -> int:
        schema = AfelNamespacesManager().schema_ns
        rdf = self.rdf
        graph.add((rdf, RDF.type, schema.Question))
        graph.add((rdf, schema.identifier, Literal(self.fullid)))
        graph.add((rdf, schema.text, Literal(self.text)))
        graph.add((rdf, schema.isPartOf, self.questionnaire.rdf))

        return 4


class Answer(RdfRepresentation, metaclass=ABCMeta):
    def __init__(self, user: User, date, question: Question):
        self.user = user
        self.question = question
        self.date = date
        self.id = self.question.fullid + "_" + self.user.userid


class CommentAnswer(Answer):
    def __init__(self, user: User, date, question: Question, text):
        super().__init__(user, date, question)
        self.text = text

    @property
    def rdf(self) -> URIRef:
        schema = AfelNamespacesManager().schema_ns
        return concatenate_uriref(schema.Answer, self.id)

    def dump_to_graph(self, graph: Graph) -> int:
        schema = AfelNamespacesManager().schema_ns
        # Create Comment
        rdf_answer = self.rdf
        graph.add((rdf_answer, RDF.type, schema.Answer))
        graph.add((rdf_answer, schema.identifier, Literal(self.id)))
        graph.add((rdf_answer, schema.text, Literal(self.text)))
        # Create CommentAction
        rdf_action = concatenate_uriref(schema.CommentAction, self.id)
        graph.add((rdf_action, RDF.type, schema.CommentAction))
        graph.add((rdf_action, schema.identifier, Literal(self.id)))
        graph.add((rdf_action, schema.startTime, Literal(self.date)))
        graph.add((rdf_action, schema.endTime, Literal(self.date)))
        # Link both comment and commentAction to user
        graph.add((rdf_answer, schema.author, self.user.rdf))
        graph.add((rdf_action, schema.agent, self.user.rdf))
        # Link CommentAction to Comment and CommentAction to Question
        graph.add((rdf_action, schema.resultComment, rdf_answer))
        graph.add((rdf_action, schema.object, self.question.rdf))

        return 11


class RatingAnswer(Answer):
    def __init__(self, user: User, date, question: Question, value):
        super().__init__(user, date, question)
        self.value = value

    @property
    def rdf(self) -> URIRef:
        schema = AfelNamespacesManager().schema_ns
        return concatenate_uriref(schema.Rating, self.id)

    def dump_to_graph(self, graph: Graph) -> int:
        schema = AfelNamespacesManager().schema_ns
        # Create Comment
        rdf_answer = self.rdf
        graph.add((rdf_answer, RDF.type, schema.Rating))
        graph.add((rdf_answer, schema.identifier, Literal(self.id)))
        graph.add((rdf_answer, schema.ratingValue, Literal(self.value)))
        # Create CommentAction
        rdf_action = concatenate_uriref(schema.ChooseAction, self.id)
        graph.add((rdf_action, RDF.type, schema.ChooseAction))
        graph.add((rdf_action, schema.identifier, Literal(self.id)))
        graph.add((rdf_action, schema.startTime, Literal(self.date)))
        graph.add((rdf_action, schema.endTime, Literal(self.date)))
        # Link both comment and commentAction to user
        graph.add((rdf_answer, schema.author, self.user.rdf))
        graph.add((rdf_action, schema.agent, self.user.rdf))
        # Link CommentAction to Comment and CommentAction to Question
        graph.add((rdf_action, schema.actionOption, rdf_answer))
        graph.add((rdf_action, schema.object, self.question.rdf))

        return 11


class IntRatingAnswer(RatingAnswer):
    def __init__(self, user: User, date, question: Question, value):
        super().__init__(user, date, question, self._any_to_int(value))

    @staticmethod
    def _any_to_int(value):
        if isinstance(value, int):
            return value
        elif isinstance(value, float):
            return round(value)
        else:
            value = str(value)
            try:
                value = int(value)
            except ValueError:
                value = round(float(value))
            return value


class FloatRatingAnswer(RatingAnswer):
    def __init__(self, user: User, date, question: Question, value):
        super().__init__(user, date, question, self._any_to_float(value))

    @staticmethod
    def _any_to_float(value):
        if isinstance(value, int):
            return float(value)
        elif isinstance(value, float):
            return value
        else:
            return float(str(value))
