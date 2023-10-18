"""
Global.health GraphQL server
"""

import json
import logging
import sys

from aiohttp import web, web_request
import graphene
from graphene_mongo import MongoengineObjectType
import graphql
from graphql import parse
from mongoengine import connect, Document
from mongoengine.fields import IntField, FloatField, StringField

from constants import (
    DATABASE_NAME,
    DB_HOST,
    DB_PORT,
    CASE_COLLECTIONS,
    RT_COLLECTIONS,
    GRAPHQL_ENDPOINT,
    GRAPHQL_PORT,
)


def setup_logger() -> None:
    """
    Set up the logger to stream at the desired level
    """

    h = logging.StreamHandler(sys.stdout)
    rootLogger = logging.getLogger()
    rootLogger.addHandler(h)
    rootLogger.setLevel(logging.DEBUG)


async def serve_graphql(request: web_request.Request) -> web.Response:
    """
    GraphQL query endpoint, receive requests, return responses

    Args:
        request (web_request.Request): A GraphQL request

    Returns:
        web.Response: A GraphQL response
    """

    logging.debug(f"Request: {request}")
    parsed_query = parse(request.query["query"])
    selection = (
        parsed_query.to_dict()
        .get("definitions", [{}])[0]
        .get("selection_set", {})
        .get("selections", [{}])[0]
    )
    arguments = selection.get("arguments", [{}])
    selection_name = selection.get("name", {}).get("value")
    pathogen_name = ""
    if arguments:
        pathogen_name = arguments[0].get("value", {}).get("value")

    # Looks like an assignment without a reference, but actually needed
    data = request

    try:
        connect(DATABASE_NAME, host=DB_HOST, port=DB_PORT)
    except Exception:
        logging.error("Could not connect to database")

    collection = ""
    if selection_name == "cases":
        collection = CASE_COLLECTIONS.get(pathogen_name)
    if selection_name == "estimates":
        collection = RT_COLLECTIONS.get(pathogen_name)

    logging.debug(f"Pathogen: {pathogen_name}, selection: {selection_name}")

    class CaseModel(Document):

        """
        Database model for case documents
        """

        meta = {"collection": collection}

        # Case demographics
        pathogen = StringField(required=True)
        caseStatus = StringField(required=True, db_field="case_status")
        pathogenStatus = StringField(required=True, db_field="pathogen_status")
        locationInformation = StringField(
            required=False, db_field="location_information"
        )
        age = StringField(required=True)
        sexAtBirth = StringField(required=True, db_field="sex_at_birth")
        setAtBirthOther = StringField(required=True, db_field="sex_at_birth_other")
        gender = StringField(required=True)
        genderOther = StringField(required=True, db_field="gender_other")
        race = StringField(required=True)
        raceOther = StringField(required=True, db_field="race_other")
        ethnicity = StringField(required=True)
        ethnicityOther = StringField(required=True, db_field="ethnicity_other")
        nationality = StringField(required=True)
        nationalityOther = StringField(required=True, db_field="nationality_other")
        occupation = StringField(required=True)
        healthcareWorker = StringField(required=True, db_field="healthcare_worker")

        # Medical history
        previousInfection = StringField(required=True, db_field="previous_infection")
        coInfection = StringField(required=True, db_field="co_infection")
        preExistingCondition = StringField(
            required=True, db_field="pre_existing_condition"
        )
        pregnancyStatus = StringField(required=True, db_field="pregnancy_status")
        vaccination = StringField(required=True)
        vaccineName = StringField(required=True, db_field="vaccine_name")
        vaccinationDate = StringField(required=True, db_field="vaccination_date")
        vaccineSideEffects = StringField(required=True, db_field="vaccine_side_effects")

        # Clinical presentation
        symptoms = StringField(required=True)
        dateOnset = StringField(required=True, db_field="date_onset")
        dateConfirmation = StringField(required=False, db_field="date_confirmation")
        confirmationMethod = StringField(required=False, db_field="confirmation_method")
        dateOfFirstConsulation = StringField(
            required=False, db_field="date_of_first_consultation"
        )
        hospitalized = StringField(required=False)
        reasonForHospitalization = StringField(
            required=False, db_field="reason_for_hospitalization"
        )
        dateHospitalization = StringField(
            required=False, db_field="date_hospitalization"
        )
        dateDischargeHospital = StringField(
            required=False, db_field="date_discharge_hospital"
        )
        intensiveCare = StringField(required=False, db_field="intensive_care")
        dateAdmissionICU = StringField(required=False, db_field="date_admission_icu")
        dateDischargeICU = StringField(required=False, db_field="date_discharge_icu")
        homeMonitoring = StringField(required=False, db_field="home_monitoring")
        isolated = StringField(required=False)
        dateIsolation = StringField(required=False, db_field="date_isolation")
        outcome = StringField(required=False)
        dateDeath = StringField(required=False, db_field="date_death")
        dateRecovered = StringField(required=False, db_field="date_recovered")

        # Exposure
        contactWithCase = StringField(required=False, db_field="contact_with_case")
        contactId = StringField(required=False, db_field="contact_id")
        contactSetting = StringField(required=False, db_field="contact_setting")
        contactSettingOther = StringField(
            required=False, db_field="contact_setting_other"
        )
        contactAnimal = StringField(required=False, db_field="contact_animal")
        contactComment = StringField(required=False, db_field="contact_comment")
        transmission = StringField(required=False)
        travelHistory = StringField(required=False, db_field="travel_history")
        travelHistoryEntry = StringField(
            required=False, db_field="travel_history_entry"
        )
        travelHistoryStart = StringField(
            required=False, db_field="travel_history_start"
        )
        travelHistoryLocation = StringField(
            required=False, db_field="travel_history_location"
        )

        # Laboratory information
        genomicsMetadata = StringField(required=False, db_field="genomics_metadata")
        accessionNumber = StringField(required=False, db_field="accession_number")

        # Source information
        source = StringField(required=False)
        sourceII = StringField(required=False, db_field="source_ii")
        sourceIII = StringField(required=False, db_field="source_iii")
        sourceIV = StringField(required=False, db_field="source_iv")
        dateEntry = StringField(required=False, db_field="date_entry")
        dateLastModified = StringField(required=False, db_field="date_last_modified")

        # Curator information (private)
        createdBy = StringField(required=False)
        verifiedBy = StringField(required=False)

    class Case(MongoengineObjectType):
        class Meta:
            model = CaseModel

    class CaseQuery(graphene.ObjectType):

        """
        GraphQL query for cases
        """

        cases = graphene.List(Case, pathogen=graphene.String(required=True))

        # Do not show cases w/o "validatedBy" entry
        # Do not show curator fields
        # https://docs.mongoengine.org/guide/querying.html#retrieving-a-subset-of-fields
        # if fields that are not downloaded are accessed, their default value (or None if no default value is provided) will be given
        def resolve_cases(
            self, info: graphql.type.definition.GraphQLResolveInfo, pathogen: str
        ) -> list:
            """
            Resolve query for cases

            Args:
                info (graphql.type.definition.GraphQLResolveInfo): query AST and more execution information
                pathogen (str): Pathogen name

            Returns:
                list: Case data
            """

            return list(
                CaseModel.objects(verifiedBy__exists=True)
                .exclude("createdBy")
                .exclude("verifiedBy")
            )

    class RtEstimateModel(Document):

        """
        Database model for R(t) estimation data
        """

        meta = {"collection": collection}
        date = StringField(required=False)
        cases = IntField(required=False)
        rMean = FloatField(required=False)
        rVar = FloatField(required=False)
        qLower = FloatField(required=False)
        qUpper = FloatField(required=False)

        # Curator information (private)
        createdBy = StringField(required=False)
        verifiedBy = StringField(required=False)

    class RtEstimate(MongoengineObjectType):
        class Meta:
            model = RtEstimateModel

    class RtEstimateQuery(graphene.ObjectType):

        """
        GraphQL query for R(t) estimates
        """

        estimates = graphene.List(RtEstimate, pathogen=graphene.String(required=True))

        def resolve_estimates(
            self, info: graphql.type.definition.GraphQLResolveInfo, pathogen: str
        ) -> list:
            """Summary

            Args:
                info (graphql.type.definition.GraphQLResolveInfo): query AST and more execution information
                pathogen (str): Pathogen name

            Returns:
                list: R(t) estimates
            """

            return list(RtEstimateModel.objects.all())

    class Query(CaseQuery, RtEstimateQuery):

        """
        Wrapper to use multiple resolvers with one endpoint
        """

        pass

    schema = graphene.Schema(query=Query, types=[Case, RtEstimate])
    query = request.query["query"]
    result = schema.execute(query)
    if result.errors:
        # Brittle, not sure how to improve
        if "not provided" in result.errors[0].message:
            return web.Response(
                text="Required argument not provided in query", status=400
            )
        if not collection:
            return web.Response(
                text=f"No {selection_name} available for pathogen {pathogen_name}",
                status=400,
            )
        logging.error(f"Error during query: {result.errors}")
        return web.Response(
            text="Server error, please contact us if this persists", status=500
        )
    return web.Response(text=json.dumps(result.data), status=200)


def run_graphql_server() -> None:
    """
    Run the GraphQL server
    """

    app = web.Application()
    app.router.add_get(f"/{GRAPHQL_ENDPOINT}", serve_graphql)
    app.router.add_get(f"/health", lambda _: web.Response(text="OK", status=200))
    web.run_app(app, port=GRAPHQL_PORT)


if __name__ == "__main__":
    setup_logger()
    logging.info("Starting GraphQL server")
    run_graphql_server()
