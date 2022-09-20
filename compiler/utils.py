from dataclasses import dataclass
from tests.benchmark import BenchmarkOutput
from tests.statistics import CircuitStatistics, TimingStatistics, CommunicationStatistics, TimingDatapoint

import struct
import json
import socket


@dataclass
class StatsForInputConfig:
    label: str
    gmw: list[BenchmarkOutput]
    gmw_vec: list[BenchmarkOutput]
    bmr: list[BenchmarkOutput]
    bmr_vec: list[BenchmarkOutput]

    @classmethod
    def from_dictionary(cls, params):
        label = params['label']

        if 'gmw' in params:
            gmw = params['gmw']
        else:
            gmw = [params['gmw_p0'], params['gmw_p1']]

        if 'gmw_vec' in params:
            gmw_vec = params['gmw_vec']
        else:
            gmw_vec = [params['gmw_vec_p0'], params['gmw_vec_p1']]

        if 'bmr' in params:
            bmr = params['bmr']
        else:
            bmr = [params['bmr_p0'], params['bmr_p1']]

        if 'bmr_vec' in params:
            bmr_vec = params['bmr_vec']
        else:
            bmr_vec = [params['bmr_vec_p0'], params['bmr_vec_p1']]

        return cls(
            label=label,
            gmw=gmw,
            gmw_vec=gmw_vec,
            bmr=bmr,
            bmr_vec=bmr_vec
        )

    def to_dictionary(self):
        return {
            'label': self.label,
            'gmw': self.gmw,
            'gmw_vec': self.gmw_vec,
            'bmr': self.bmr,
            'bmr_vec': self.bmr_vec,
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
class PartyReadyReq:
    id: int

    @classmethod
    def from_dictionary(cls, params):
        id = params['id']
        return cls(id=id)

    def to_dictionary(self):
        return {'id': self.id
                }


@dataclass
class GetAddressResp:
    client_address: (str, int)  # (address, port)

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
    party_addrs: list[str]
    cmd_args: list[str]
    benchmark_name: str
    protocol: str
    vectorized: bool

    @classmethod
    def from_dictionary(cls, params):
        party_addrs = params['party_addrs']
        cmd_args = params['cmd_args']
        benchmark_name = params['benchmark_name']
        protocol = params['protocol']
        vectorized = params['vectorized']

        return cls(
            party_addrs=party_addrs,
            cmd_args=cmd_args,
            benchmark_name=benchmark_name,
            protocol=protocol,
            vectorized=vectorized
        )

    def to_dictionary(self):
        return {
            'party_addrs': self.party_addrs,
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
    if isinstance(python_object, TimingDatapoint):
        return {'__class__': 'TimingDatapoint',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, CommunicationStatistics):
        return {'__class__': 'CommunicationStatistics',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, TimingStatistics):
        return {'__class__': 'TimingStatistics',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, CircuitStatistics):
        return {'__class__': 'CircuitStatistics',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, BenchmarkOutput):
        return {'__class__': 'BenchmarkOutput',
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
    elif isinstance(python_object, PartyReadyReq):
        return {'__class__': 'PartyReadyReq',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, GetAddressResp):
        return {'__class__': 'GetAddressResp',
                '__value__': python_object.to_dictionary()}

    raise TypeError(repr(python_object) + ' is not JSON serializable')


def _from_json(json_object):
    if '__class__' in json_object:
        if json_object['__class__'] == 'TimingDatapoint':
            return TimingDatapoint.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'CommunicationStatistics':
            return CommunicationStatistics.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'TimingStatistics':
            return TimingStatistics.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'CircuitStatistics':
            return CircuitStatistics.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'BenchmarkOutput':
            return BenchmarkOutput.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'StatsForTask':
            return StatsForTask.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'StatsForInputConfig':
            return StatsForInputConfig.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'RunBenchmarkReq':
            return RunBenchmarkReq.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'PartyReadyReq':
            return PartyReadyReq.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'GetAddressResp':
            return GetAddressResp.from_dictionary(json_object['__value__'])

    return json_object


def _read_socket_buf(conn: socket, n: int):
    buf = b''
    while len(buf) < n:
        new_data = conn.recv(n - len(buf))
        if not new_data:
            return None
        buf += new_data
    return buf
