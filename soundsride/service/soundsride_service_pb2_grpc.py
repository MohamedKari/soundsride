# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from soundsride.service import soundsride_service_pb2 as soundsride_dot_service_dot_soundsride__service__pb2


class SoundsRideStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Ping = channel.unary_unary(
                '/SoundsRide/Ping',
                request_serializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.SerializeToString,
                response_deserializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.FromString,
                )
        self.StartSession = channel.unary_unary(
                '/SoundsRide/StartSession',
                request_serializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.SerializeToString,
                response_deserializer=soundsride_dot_service_dot_soundsride__service__pb2.StartSessionResponse.FromString,
                )
        self.UpdateTransitionSpec = channel.unary_unary(
                '/SoundsRide/UpdateTransitionSpec',
                request_serializer=soundsride_dot_service_dot_soundsride__service__pb2.UpdateTransitionSpecRequest.SerializeToString,
                response_deserializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.FromString,
                )
        self.GetChunk = channel.unary_unary(
                '/SoundsRide/GetChunk',
                request_serializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.SerializeToString,
                response_deserializer=soundsride_dot_service_dot_soundsride__service__pb2.AudioChunkResponse.FromString,
                )
        self.GetPosition = channel.unary_unary(
                '/SoundsRide/GetPosition',
                request_serializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.SerializeToString,
                response_deserializer=soundsride_dot_service_dot_soundsride__service__pb2.Position.FromString,
                )


class SoundsRideServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Ping(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def StartSession(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def UpdateTransitionSpec(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetChunk(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def GetPosition(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_SoundsRideServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Ping': grpc.unary_unary_rpc_method_handler(
                    servicer.Ping,
                    request_deserializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.FromString,
                    response_serializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.SerializeToString,
            ),
            'StartSession': grpc.unary_unary_rpc_method_handler(
                    servicer.StartSession,
                    request_deserializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.FromString,
                    response_serializer=soundsride_dot_service_dot_soundsride__service__pb2.StartSessionResponse.SerializeToString,
            ),
            'UpdateTransitionSpec': grpc.unary_unary_rpc_method_handler(
                    servicer.UpdateTransitionSpec,
                    request_deserializer=soundsride_dot_service_dot_soundsride__service__pb2.UpdateTransitionSpecRequest.FromString,
                    response_serializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.SerializeToString,
            ),
            'GetChunk': grpc.unary_unary_rpc_method_handler(
                    servicer.GetChunk,
                    request_deserializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.FromString,
                    response_serializer=soundsride_dot_service_dot_soundsride__service__pb2.AudioChunkResponse.SerializeToString,
            ),
            'GetPosition': grpc.unary_unary_rpc_method_handler(
                    servicer.GetPosition,
                    request_deserializer=soundsride_dot_service_dot_soundsride__service__pb2.Empty.FromString,
                    response_serializer=soundsride_dot_service_dot_soundsride__service__pb2.Position.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'SoundsRide', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class SoundsRide(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Ping(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/SoundsRide/Ping',
            soundsride_dot_service_dot_soundsride__service__pb2.Empty.SerializeToString,
            soundsride_dot_service_dot_soundsride__service__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def StartSession(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/SoundsRide/StartSession',
            soundsride_dot_service_dot_soundsride__service__pb2.Empty.SerializeToString,
            soundsride_dot_service_dot_soundsride__service__pb2.StartSessionResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def UpdateTransitionSpec(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/SoundsRide/UpdateTransitionSpec',
            soundsride_dot_service_dot_soundsride__service__pb2.UpdateTransitionSpecRequest.SerializeToString,
            soundsride_dot_service_dot_soundsride__service__pb2.Empty.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetChunk(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/SoundsRide/GetChunk',
            soundsride_dot_service_dot_soundsride__service__pb2.Empty.SerializeToString,
            soundsride_dot_service_dot_soundsride__service__pb2.AudioChunkResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def GetPosition(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/SoundsRide/GetPosition',
            soundsride_dot_service_dot_soundsride__service__pb2.Empty.SerializeToString,
            soundsride_dot_service_dot_soundsride__service__pb2.Position.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
