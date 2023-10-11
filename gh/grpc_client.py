"""
Global.health gRPC client
"""

import logging

import grpc

from cases_pb2 import CasesRequest, CasesResponse
from cases_pb2_grpc import CasesStub

from rt_estimate_pb2 import RtEstimateRequest, RtEstimateResponse
from rt_estimate_pb2_grpc import RtEstimatesStub
from constants import Partner, RT_PARAMS


def get_credentials(token: str, certificate: bytes) -> grpc.ChannelCredentials:
    token_credentials = grpc.access_token_call_credentials(token)
    channel_credentials = grpc.ssl_channel_credentials(certificate)
    credentials = grpc.composite_channel_credentials(
        channel_credentials, token_credentials
    )
    return credentials


def get_metadata(token: str) -> list[tuple]:
    """
    Create request metadata

    Args:
        token (str): JWT

    Returns:
        list[tuple]: request metadata
    """
    jwt_header = ("authorization", f"bearer {token}")
    return [jwt_header]


def get_partner_cases(
    pathogen: str, partner: Partner, credentials: grpc.ChannelCredentials
) -> CasesResponse:
    """
    Get case data from a partner

    Args:
        pathogen (str): Name of the pathogen
        partner (Partner): Partner configuration
        credentials (grpc.ChannelCredentials): gRPC channel credentials

    Returns:
        CasesResponse: Response with case data
    """

    logging.debug(
        f"Getting {pathogen} cases from {partner.grpc_host}:{partner.grpc_port}"
    )
    channel = grpc.secure_channel(
        f"{partner.grpc_host}:{partner.grpc_port}", credentials
    )
    client = CasesStub(channel)
    response = client.GetCases(CasesRequest(pathogen=pathogen))
    return response


def get_partner_rt_estimates(
    pathogen: str, partner: Partner, credentials: grpc.ChannelCredentials
) -> RtEstimateResponse:
    """
    Get R(t) estimate data from a partner

    Args:
        pathogen (str): Name of the pathogen
        partner (Partner): Partner configuration
        credentials (grpc.ChannelCredentials): gRPC channel credentials

    Returns:
        RtEstimateResponse: Response with R(t) estimate data
    """

    logging.debug(
        f"Getting {pathogen} R(t) estimates from {partner.grpc_host}:{partner.grpc_port}"
    )
    channel = grpc.secure_channel(
        f"{partner.grpc_host}:{partner.grpc_port}", credentials
    )
    client = RtEstimatesStub(channel)
    request = RtEstimateRequest(
        pathogen=pathogen,
        start_date=RT_PARAMS.get("start_date"),
        end_date=RT_PARAMS.get("end_date"),
        q_lower=RT_PARAMS.get("q_lower"),
        q_upper=RT_PARAMS.get("q_upper"),
        gt_distribution=RT_PARAMS.get("gt_distribution"),
        delay_distribution=RT_PARAMS.get("delay_distribution"),
    )
    response = client.GetRtEstimates(request)
    return response
