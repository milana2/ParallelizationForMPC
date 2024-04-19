from dataclasses import dataclass
from tests.backends.motion.benchmark import BenchmarkOutput as CombineBenchmarkOutput
from tests.backends.motion.statistics import CircuitStatistics as CombineCircuitStatistics
from tests.backends.motion.statistics import TimingStatistics as CombineTimingStatistics
from tests.backends.motion.statistics import CommunicationStatistics as CombineCommunicationStatistics 
from tests.backends.motion.statistics import TimingDatapoint as CombineTimingDatapoint

import struct
import json

@dataclass
class StatsForInputConfig:
    label: str
    gmw_p0: CombineBenchmarkOutput
    gmw_p1: CombineBenchmarkOutput
    gmw_vec_p0: CombineBenchmarkOutput
    gmw_vec_p1: CombineBenchmarkOutput
    bmr_p0: CombineBenchmarkOutput
    bmr_p1: CombineBenchmarkOutput
    bmr_vec_p0: CombineBenchmarkOutput
    bmr_vec_p1: CombineBenchmarkOutput

    @classmethod
    def from_dictionary(cls, params):
        label = params['label']
        gmw_p0 = params['gmw_p0']
        gmw_p1 = params['gmw_p1']
        gmw_vec_p0 = params['gmw_vec_p0']
        gmw_vec_p1 = params['gmw_vec_p1']
        bmr_p0 = params['bmr_p0']
        bmr_p1 = params['bmr_p1']
        bmr_vec_p0 = params['bmr_vec_p0']
        bmr_vec_p1 = params['bmr_vec_p1']

        return cls(
            label=label,
            gmw_p0=gmw_p0,
            gmw_p1=gmw_p1,
            gmw_vec_p0=gmw_vec_p0,
            gmw_vec_p1=gmw_vec_p1,
            bmr_p0=bmr_p0,
            bmr_p1=bmr_p1,
            bmr_vec_p0=bmr_vec_p0,
            bmr_vec_p1=bmr_vec_p1
            )

    def to_dictionary(self):
        return {
            'label': self.label,
            'gmw_p0': self.gmw_p0,
            'gmw_p1': self.gmw_p1,
            'gmw_vec_p0': self.gmw_vec_p0,
            'gmw_vec_p1': self.gmw_vec_p1,
            'bmr_p0': self.bmr_p0,
            'bmr_p1': self.bmr_p1,
            'bmr_vec_p0': self.bmr_vec_p0,
            'bmr_vec_p1': self.bmr_vec_p1,
        }


@dataclass
class StatsForTask:
    label: str
    input_configs: list[StatsForInputConfig]

    @classmethod
    def from_dictionary(cls, params):
        label = params['label']
        input_configs = params['input_configs']
        return cls(
            label=label,
            input_configs=input_configs
            )

    def to_dictionary(self):
        return {'label': self.label,
                'input_configs': self.input_configs
                }


@dataclass
class GetAddressReq:

    @classmethod
    def from_dictionary(cls, params):
        return cls()

    def to_dictionary(self):
        return {}

@dataclass
class GetAddressResp:
    client_address: tuple[str, int] # [address, port]

    @classmethod
    def from_dictionary(cls, params):
        client_address = params['client_address']

        return cls(
            client_address=client_address,
            )

    def to_dictionary(self):
        return {
            'client_address': self.client_address,
        }

@dataclass
class RunBenchmarkReq:
    party0_mpc_addr: str
    party1_mpc_addr: str
    cmd_args: list[str]
    benchmark_name: str
    protocol: str
    vectorized: bool

    @classmethod
    def from_dictionary(cls, params):
        party0_mpc_addr = params['party0_mpc_addr']
        party1_mpc_addr = params['party1_mpc_addr']
        cmd_args = params['cmd_args']
        benchmark_name = params['benchmark_name']
        protocol = params['protocol']
        vectorized = params['vectorized']

        return cls(
            party0_mpc_addr=party0_mpc_addr,
            party1_mpc_addr=party1_mpc_addr,
            cmd_args=cmd_args,
            benchmark_name=benchmark_name,
            protocol=protocol,
            vectorized=vectorized
            )

    def to_dictionary(self):
        return {
            'party0_mpc_addr': self.party0_mpc_addr,
            'party1_mpc_addr': self.party1_mpc_addr,
            'cmd_args': self.cmd_args,
            'benchmark_name': self.benchmark_name,
            'protocol': self.protocol,
            'vectorized': self.vectorized
        }


def json_serialize(obj):
    return json.dumps(obj, default=_to_json)

def json_deserialize(json_str):
    return json.loads(json_str, object_hook=_from_json)


def read_message(conn):
    buf = _read_socket_buf(conn, 4)
    if not buf:
        # print("Error: Unable to read message size")
        return None

    msg_size = struct.unpack("!i", buf)[0]
    # print("Length of the message is: {}".format(msg_size))

    buf = _read_socket_buf(conn, msg_size)
    if not buf:
        # print("Error: Unable to read message of length {}".format(msg_size))
        return None

    obj = json.loads(buf.decode("utf-8"), object_hook=_from_json)
    return obj


def write_message(conn, obj):
    msg = json.dumps(obj, default=_to_json).encode('utf-8')
    msg_size = len(msg)
    buf_to_write = struct.pack("!i", msg_size) + msg
    conn.sendall(buf_to_write)

# --- Private Functions --

def _to_json(python_object):
    if isinstance(python_object, CombineTimingDatapoint):
        return  {'__class__': 'CombineTimingDatapoint',
                 '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, CombineCommunicationStatistics):
        return {'__class__': 'CombineCommunicationStatistics',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, CombineTimingStatistics):
        return {'__class__': 'CombineTimingStatistics',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, CombineCircuitStatistics):
        return {'__class__': 'CombineCircuitStatistics',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, CombineBenchmarkOutput):
        return {'__class__': 'CombineBenchmarkOutput',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, StatsForTask):
        return {'__class__': 'StatsForTask',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, StatsForInputConfig):
        return {'__class__': 'StatsForInputConfig',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, RunBenchmarkReq):
        return {'__class__': 'RunBenchmarkReq',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, GetAddressReq):
        return {'__class__': 'GetAddressReq',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, GetAddressResp):
        return {'__class__': 'GetAddressResp',
                '__value__': python_object.to_dictionary()}

    raise TypeError(repr(python_object) + ' is not JSON serializable')


def _from_json(json_object):
    if '__class__' in json_object:
        if json_object['__class__'] == 'TimingDatapoint' or json_object['__class__'] == 'CombineTimingDatapoint':
            return CombineTimingDatapoint.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'CommunicationStatistics' or json_object['__class__'] == 'CombineCommunicationStatistics':
            return CombineCommunicationStatistics.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'TimingStatistics' or json_object['__class__'] == 'CombineTimingStatistics':
            return CombineTimingStatistics.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'CircuitStatistics' or json_object['__class__'] == 'CombineCircuitStatistics':
            return CombineCircuitStatistics.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'BenchmarkOutput' or json_object['__class__'] == 'CombineBenchmarkOutput':
            return CombineBenchmarkOutput.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'StatsForTask':
            return StatsForTask.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'StatsForInputConfig':
            return StatsForInputConfig.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'RunBenchmarkReq':
            return RunBenchmarkReq.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'GetAddressReq':
            return GetAddressReq.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'GetAddressResp':
            return GetAddressResp.from_dictionary(json_object['__value__'])

    return json_object


def _read_socket_buf(conn, n):
    buf = b''
    while len(buf) < n:
        new_data = conn.recv(n - len(buf))
        if not new_data:
            return None
        buf += new_data
    return buf

