import logging

import grpc

from cases_pb2 import CasesRequest, CasesResponse
from cases_pb2_grpc import CasesStub

from model_comparison_pb2 import ModelComparisonRequest, ModelComparisonResponse
from model_comparison_pb2_grpc import ModelComparisonsStub

from rt_estimate_pb2 import RtEstimateRequest, RtEstimateResponse
from rt_estimate_pb2_grpc import RtEstimatesStub
from constants import Partner, RT_PARAMS


def get_metadata(token: str) -> list[tuple]:
    jwt_header = ("authorization", f"bearer {token}")
    return [jwt_header]


def get_partner_cases(pathogen: str, partner: Partner, metadata: list[tuple]) -> CasesResponse:
    logging.debug(f"Getting {pathogen} cases from {partner.grpc_host}:{partner.grpc_port}")
    channel = grpc.insecure_channel(f"{partner.grpc_host}:{partner.grpc_port}")
    client = CasesStub(channel)
    response = client.GetCases(CasesRequest(pathogen=pathogen), metadata=metadata)
    # logging.debug(f"Got cases {response.cases}")
    return response


def get_partner_rt_estimates(pathogen: str, partner: Partner, metadata: list[tuple]) -> RtEstimateResponse:
    logging.debug(f"Getting {pathogen} R(t) estimates from {partner.grpc_host}:{partner.grpc_port}")
    channel = grpc.insecure_channel(f"{partner.grpc_host}:{partner.grpc_port}")
    client = RtEstimatesStub(channel)
    request = RtEstimateRequest(
        pathogen=pathogen,
        start_date=RT_PARAMS.get("start_date"),
        end_date=RT_PARAMS.get("end_date"),
        q_lower=RT_PARAMS.get("q_lower"),
        q_upper=RT_PARAMS.get("q_upper"),
        gt_distribution=RT_PARAMS.get("gt_distribution"),
        delay_distribution=RT_PARAMS.get("delay_distribution")
    )
    response = client.GetRtEstimates(request, metadata=metadata)
    # logging.debug(f"Got estimates {response.estimates}")
    return response


def get_partner_comparisons(pathogen: str, partner: Partner, metadata: list[tuple]) -> ModelComparisonResponse:
    logging.debug(f"Getting model comparisons from {partner.grpc_host}:{partner.grpc_port}")
    channel = grpc.insecure_channel(f"{partner.grpc_host}:{partner.grpc_port}")
    client = ModelComparisonsStub(channel)
    response = client.GetModelComparisons(
        ModelComparisonRequest(information_criterion="loo"), metadata=metadata
    )
    # logging.debug(f"Got cases {response.cases}")
    return response
