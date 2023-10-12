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
    pathogen: str, partner: Partner, metadata: list[tuple]
) -> CasesResponse:
    """
    Get case data from a partner

    Args:
        pathogen (str): Name of the pathogen
        partner (Partner): Partner configuration
        metadata (list[tuple]): request metadata

    Returns:
        CasesResponse: Response with case data
    """
    logging.debug(
        f"Getting {pathogen} cases from {partner.grpc_host}:{partner.grpc_port}"
    )
    channel = grpc.insecure_channel(f"{partner.grpc_host}:{partner.grpc_port}")
    client = CasesStub(channel)
    response = client.GetCases(CasesRequest(pathogen=pathogen), metadata=metadata)
    # logging.debug(f"Got cases {response.cases}")
    return response


def get_partner_rt_estimates(
    pathogen: str, partner: Partner, metadata: list[tuple]
) -> RtEstimateResponse:
    """
    Get R(t) estimate data from a partner

    Args:
        pathogen (str): Name of the pathogen
        partner (Partner): Partner configuration
        metadata (list[tuple]): request metadata

    Returns:
        RtEstimateResponse: Response with R(t) estimate data
    """
    logging.debug(
        f"Getting {pathogen} R(t) estimates from {partner.grpc_host}:{partner.grpc_port}"
    )
    channel = grpc.insecure_channel(f"{partner.grpc_host}:{partner.grpc_port}")
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
    response = client.GetRtEstimates(request, metadata=metadata)
    # logging.debug(f"Got estimates {response.estimates}")
    return response
