from pathlib import Path
import signal
from concurrent.futures import ThreadPoolExecutor
from soundsride.mix_plan import MixPlanViz, TransitionSpec
import sys
import time
from io import BytesIO
import inspect

import logging
from typing import Dict

import pydub
import grpc
from google.protobuf.json_format import MessageToJson
from . import soundsride_service_pb2_grpc
import fire


from ..session import SoundsRideSession
from ..vehicle.gps_client import MibInterface

from .soundsride_service_pb2 import (
    AudioChunkResponse, 
    StartSessionResponse, 
    UpdateTransitionSpecRequest,
    Position,
    Empty)

# reenable if segmentation faults occur (e. g. for SIGTERMs interrupting background threads)
# import faulthandler; faulthandler.enable()

from .. import log
log.setup_logger()

MIB_HOST = "mib"

class RpcHandlingException(Exception):
    def __init__(self):
        super().__init__()
        self.rpc_name = inspect.stack()[1][3]

    def __str__(self):
        error_str = (
            f" \n"
            f"Error during handling RPC with name {self.rpc_name}.\n" 
            f"Error type was: {type(self.__cause__)}\n"
            f"Error message was: {self.__cause__} \n"
        )

        logging.error(error_str)
        return error_str


class SoundsRideServicer(soundsride_service_pb2_grpc.SoundsRideServicer):

    def __init__(self, mib_host, app_model=None) -> None:
        super().__init__()
        self.sessions: Dict[int, SoundsRideSession] = dict()
        self.app_model = app_model
        self.mib_host = mib_host
        self.log = True


    def log_request(self, request, context): # pylint: disable=unused-argument
        logging.getLogger(__name__).debug(
            "Received gRPC request for method %s by peer %s with metadata %s", 
            inspect.stack()[1][3],
            context.peer(),
            context.invocation_metadata())


    def Ping(self, request: Empty, context: grpc.RpcContext) -> Empty:
        try:
            self.log_request(request, context)
            return Empty()
        except Exception as e:
            raise RpcHandlingException() from e


    def StartSession(self, request: Empty, context: grpc.RpcContext) -> StartSessionResponse:
        try:
            self.log_request(request, context)

            new_session_id = len(self.sessions)

            session_log_id = int(time.time() * 1000)
            self.sessions[new_session_id] = SoundsRideSession(self.app_model, session_log_id=session_log_id)

            if self.log:
                Path(f"log/{session_log_id}").mkdir(parents=True, exist_ok=True)

            return StartSessionResponse(session_id=new_session_id)
        except Exception as e:
            raise RpcHandlingException() from e


    def UpdateTransitionSpec(self, request: UpdateTransitionSpecRequest, context: grpc.RpcContext) -> Empty():
        try:
            self.log_request(request, context)
            logging.getLogger(__name__).debug("Session ID is %s", request.session_id)
            # logging.getLogger(__name__).debug("UpdateTransitionSpecRequest %s", request)

            request_log_id = None

            session = self.sessions[request.session_id]
            
            if self.log:
                request_log_id = int(time.time() * 1000)

                json_dump = MessageToJson(request, indent=4, including_default_value_fields=True)
                path = Path(f"log/{session.session_log_id}/{request_log_id}.json")
                path.parent.mkdir(exist_ok=True, parents=True)
                Path.write_text(path, json_dump)
                

            # session.update_mix_plan(etts, transition_tos, transition_ids)
            session.update_mix_plan(request, request_log_id=request_log_id)
            
            return Empty()
        except Exception as e:
            raise RpcHandlingException() from e


    def GetChunk(self, request: UpdateTransitionSpecRequest, context: grpc.RpcContext) -> AudioChunkResponse:
        try:
            self.log_request(request, context)

            first_frame_id = 0

            segment = pydub.AudioSegment.from_mp3("/Users/mo/code/soundsride/tests/data/tsunami.mp3")
            
            subsegment_bytes_io = BytesIO()
            
            subsegment = segment[0:10_000]
            subsegment.export(subsegment_bytes_io, format="f32le")
            print("subsegment.channels", subsegment.channels)

            subsegment_bytes = subsegment_bytes_io.getvalue()
            print("len(subsegment_bytes)", len(subsegment_bytes), flush=True)

            logging.getLogger(__name__).debug("Sending audio chunk")
            
            return AudioChunkResponse(first_frame_id=first_frame_id, audio_chunk=subsegment_bytes)
        except Exception as e:
            raise RpcHandlingException() from e


    def GetPosition(self, request: UpdateTransitionSpecRequest, context: grpc.RpcContext) -> AudioChunkResponse:
        try:
            self.log_request(request, context)

            mib_interface = MibInterface(self.mib_host)
            track_precision_data = mib_interface.fetch_track_precision()

            gps_position = track_precision_data[0]["currentDataPoint"]["gpsPosition"]
            lat, lng, alt = gps_position.split(";")
            lat, lng, alt = float(lat), float(lng), float(alt)

            position = Position(latitude=lat, longitude=lng, altitude=alt)
            return position
        except Exception as e:
            raise RpcHandlingException() from e
    


class GrpcServer:

    def __init__(self, mib_host: str, app_model=None) -> None:
        self.server = self._create_server(mib_host, app_model=app_model)

    def get_server_credentials(self): 
        # https://www.sandtable.com/using-ssl-with-grpc-in-python/
        with open("privkey.pem", "rb") as f:
            private_key = f.read()
        
        with open("server.crt", "rb") as f:
            cert = f.read()

        server_credentials = grpc.ssl_server_credentials([(private_key, cert)])
        return server_credentials

    @staticmethod
    def register_stop_signal_handler(grpc_server):

        def signal_handler(signalnum, _):
            print("Processing signal %s received...", signalnum)
            grpc_server.stop(None)
            sys.exit("Exiting after cancel request.")

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


    @staticmethod
    def _create_server(mib_host, port: int = 8888, app_model=None) -> grpc.Server:    
        server = grpc.server(
            ThreadPoolExecutor(max_workers=10),
            options=[
                ("grpc.max_send_message_length", 100_000_000),
                ("grpc.max_receive_message_length", 100_000_000),
                ("grpc.max_message_length", 100_000_000)
            ])

        soundsride_service_pb2_grpc.add_SoundsRideServicer_to_server(
            SoundsRideServicer(mib_host, app_model=app_model),
            server
        )
        
        # server.add_secure_port(f"[::]:{port}", get_server_credentials())
        server.add_insecure_port(f"0.0.0.0:{port}")
        logging.getLogger(__name__).debug("Starting gRPC server...")
        
        GrpcServer.register_stop_signal_handler(server)

        return server
        
    def start_blocking(self):
        self.server.start()
        self.server.wait_for_termination()

    def start_daemon(self):
        self.server.start()


def run(mib_host: str):
    grpc_server = GrpcServer(mib_host)
    grpc_server.start_blocking()


if __name__ == "__main__":
    fire.Fire(run)
    