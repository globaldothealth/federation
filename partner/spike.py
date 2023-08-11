from google.protobuf.json_format import MessageToDict, ParseDict
import grpc
from grpc_interceptor import ServerInterceptor
from grpc_interceptor.exceptions import GrpcException

from cases_pb2 import Case, CasesResponse
from cases_pb2_grpc import (
    add_CasesServicer_to_server,
    CasesServicer
)


print(Case)
print(vars(Case))

print(Case.DESCRIPTOR.fields)
print(Case.DESCRIPTOR.fields_by_name.keys())
print(Case.DESCRIPTOR.fields_by_name["healthcare_worker"].full_name)
print(Case.DESCRIPTOR.fields_by_name["healthcare_worker"].type)
print(Case.DESCRIPTOR.fields_by_name["healthcare_worker"].enum_type)  # None if not an enum
print(Case.DESCRIPTOR.fields_by_name["healthcare_worker"].enum_type.name)
print(Case.DESCRIPTOR.fields_by_name["healthcare_worker"].enum_type.values_by_name.keys())

