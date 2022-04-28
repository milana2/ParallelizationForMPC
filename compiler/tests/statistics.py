from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique
from typing import Optional

def median(lst: list[float]) -> float:
    assert len(lst) > 1, lst
    sorted_lst = sorted(lst)
    mid = len(sorted_lst) // 2
    median = (sorted_lst[mid] + sorted_lst[~mid]) / 2
    return median

def mean(lst: list[float]) -> float:
    assert len(lst) > 1, lst
    mean = sum(lst) / len(lst)
    return mean

def stddev(lst: list[float]) -> float:
    assert len(lst) > 1, lst
    mean = sum(lst) / len(lst)
    variance = sum([((x - mean) ** 2) for x in lst]) / len(lst)
    stddev = variance ** 0.5
    return stddev


@dataclass
class TimingDatapoint:
    datapoint_name: str

    mean: float
    median: float
    stddev: float
    # unit: str = 'ms'
    readings: list[float]

    def __init__(self, datapoint_name: str, mean: float, median: float, 
        stddev: float, readings: list[float] = []):
        self.datapoint_name = datapoint_name
        self.mean = mean
        self.median = median
        self.stddev = stddev
        self.readings = readings
        if len(self.readings) == 0:
            self.readings = [self.mean]

    @classmethod
    def from_dictionary(cls, params):
        datapoint_name = params['datapoint_name']
        mean = params['mean']
        median = params['median']
        stddev = params['stddev']
        readings = params['readings']
        return cls(
            datapoint_name=datapoint_name,
            mean=mean,
            median=median,
            stddev=stddev,
            readings=readings
            )

    def to_dictionary(self):
        return {'datapoint_name': self.datapoint_name,
                'mean': self.mean,
                'median': self.median,
                'stddev': self.stddev,
                'readings': self.readings
                }

    @classmethod
    def by_accumulating_readings(cls, a, b):
        readings = a.readings + b.readings
        mean_value = mean(readings)
        median_value = median(readings)
        stddev_value = stddev(readings)

        return cls(
            datapoint_name = a.datapoint_name,
            mean = mean_value,
            median = median_value,
            stddev = stddev_value,
            readings = readings
        )


def parse_datapoint(line: str) -> TimingDatapoint:
    line_parts = line.split()

    stddev_unit = line_parts[-1]
    assert stddev_unit == "ms"
    stddev_data = float(line_parts[-2])

    median_unit = line_parts[-3]
    assert median_unit == "ms"
    median_data = float(line_parts[-4])

    mean_unit = line_parts[-5]
    assert mean_unit == "ms"
    mean_data = float(line_parts[-6])

    datapoint_name = line_parts[:-6]

    return TimingDatapoint(
        datapoint_name=" ".join(datapoint_name),
        mean=mean_data,
        median=median_data,
        stddev=stddev_data,
    )


@dataclass
class CommunicationStatistics:
    send_size: float
    # send_unit: str = 'MiB'
    send_num_msgs: int

    recv_size: float
    # recv_unit: str = 'MiB'
    recv_num_msgs: int

    @classmethod
    def from_dictionary(cls, params):
        send_size = params['send_size']
        send_num_msgs = params['send_num_msgs']
        recv_size = params['recv_size']
        recv_num_msgs = params['recv_num_msgs']
        return cls(
            send_size=send_size,
            send_num_msgs=send_num_msgs,
            recv_size=recv_size,
            recv_num_msgs=recv_num_msgs,
            )

    def to_dictionary(self):
        return {'send_size': self.send_size,
                'send_num_msgs': self.send_num_msgs,
                'recv_size': self.recv_size,
                'recv_num_msgs': self.recv_num_msgs
                }

    @classmethod
    def by_accumulating_readings(cls, a, b):
        """
        this class contains metrics that don't change between runs
        """
        return a


def parse_communication_statistics(
    send_line: str, recv_line: str
) -> CommunicationStatistics:
    send_line_parts = send_line.split()
    assert len(send_line_parts) == 6
    assert send_line_parts[0] == "Sent:"

    send_size = float(send_line_parts[1])
    assert send_line_parts[2] == "MiB"
    send_num_msgs = int(send_line_parts[4])

    recv_line_parts = recv_line.split()
    assert len(recv_line_parts) == 6
    assert recv_line_parts[0] == "Received:"

    recv_size = float(recv_line_parts[1])
    assert recv_line_parts[2] == "MiB"
    recv_num_msgs = int(recv_line_parts[4])

    return CommunicationStatistics(
        send_size=send_size,
        send_num_msgs=send_num_msgs,
        recv_size=recv_size,
        recv_num_msgs=recv_num_msgs,
    )


@dataclass
class TimingStatistics:
    num_iterations: int

    mt_presetup: TimingDatapoint
    mt_setup: TimingDatapoint
    sp_presetup: TimingDatapoint
    sp_setup: TimingDatapoint
    sb_presetup: TimingDatapoint
    sb_setup: TimingDatapoint
    base_ots: TimingDatapoint
    ot_extension_setup: TimingDatapoint

    preprocess_total: TimingDatapoint
    gates_setup: TimingDatapoint
    gates_online: TimingDatapoint

    circuit_evaluation: TimingDatapoint

    communication: CommunicationStatistics

    @classmethod
    def from_dictionary(cls, params):
        num_iterations = params['num_iterations']
        mt_presetup = params['mt_presetup']
        mt_setup = params['mt_setup']
        sp_presetup = params['sp_presetup']
        sp_setup = params['sp_setup']
        sb_presetup = params['sb_presetup']
        sb_setup = params['sb_setup']
        base_ots = params['base_ots']
        ot_extension_setup = params['ot_extension_setup']

        preprocess_total = params['preprocess_total']
        gates_setup = params['gates_setup']
        gates_online = params['gates_online']

        circuit_evaluation = params['circuit_evaluation']

        communication = params['communication']
        return cls(
            num_iterations=num_iterations,
            mt_presetup=mt_presetup,
            mt_setup=mt_setup,
            sp_presetup=sp_presetup,
            sp_setup=sp_setup,
            sb_presetup=sb_presetup,
            sb_setup=sb_setup,
            base_ots=base_ots,
            ot_extension_setup=ot_extension_setup,
            preprocess_total=preprocess_total,
            gates_setup=gates_setup,
            gates_online=gates_online,
            circuit_evaluation=circuit_evaluation,
            communication=communication,
            )

    def to_dictionary(self):
        return {'num_iterations': self.num_iterations,
                'mt_presetup': self.mt_presetup,
                'mt_setup': self.mt_setup,
                'sp_presetup': self.sp_presetup,
                'sp_setup': self.sp_setup,
                'sb_presetup': self.sb_presetup,
                'sb_setup': self.sb_setup,
                'base_ots': self.base_ots,
                'ot_extension_setup': self.ot_extension_setup,

                'preprocess_total': self.preprocess_total,
                'gates_setup': self.gates_setup,
                'gates_online': self.gates_online,
                
                'circuit_evaluation': self.circuit_evaluation,
                
                'communication': self.communication,
                }

    @classmethod
    def by_accumulating_readings(cls, a, b):
        return cls(
           num_iterations = a.num_iterations + b.num_iterations,
           mt_presetup = TimingDatapoint.by_accumulating_readings(
            a.mt_presetup, b.mt_presetup
            ),
           mt_setup = TimingDatapoint.by_accumulating_readings(
            a.mt_setup, b.mt_setup
            ),
           sp_presetup = TimingDatapoint.by_accumulating_readings(
            a.sp_presetup, b.sp_presetup
            ),
           sp_setup = TimingDatapoint.by_accumulating_readings(
            a.sp_setup, b.sp_setup
            ),
           sb_presetup = TimingDatapoint.by_accumulating_readings(
            a.sb_presetup, b.sb_presetup
            ),
           sb_setup = TimingDatapoint.by_accumulating_readings(
            a.sb_setup, b.sb_setup
            ),
           base_ots = TimingDatapoint.by_accumulating_readings(
            a.base_ots, b.base_ots
            ),
           ot_extension_setup = TimingDatapoint.by_accumulating_readings(
            a.ot_extension_setup, b.ot_extension_setup
            ),

           preprocess_total = TimingDatapoint.by_accumulating_readings(
            a.preprocess_total, b.preprocess_total
            ),
           gates_setup = TimingDatapoint.by_accumulating_readings(
            a.gates_setup, b.gates_setup
            ),
           gates_online = TimingDatapoint.by_accumulating_readings(
            a.gates_online, b.gates_online
            ),

           circuit_evaluation = TimingDatapoint.by_accumulating_readings(
            a.circuit_evaluation, b.circuit_evaluation
            ),

           communication = CommunicationStatistics.by_accumulating_readings(
            a.communication, b.communication
            )
        )


def is_thick_boundary(line: str) -> bool:
    return all(char == "=" for char in line)


def is_thin_boundary(line: str) -> bool:
    return all(char == "-" for char in line)


def parse_timing_data(lines: list[str]) -> TimingStatistics:
    assert is_thick_boundary(lines[0])
    assert lines[1] == ""
    assert is_thick_boundary(lines[2])

    # lines[3] == "MOTION version: [VERSION] @ [BRANCH]"
    # lines[4] == "invocation: [INVOCATION]"
    # lines[5] == "by [USER]@[HOST], PID [PID]"
    assert is_thick_boundary(lines[6])

    # lines[5] == "Run time statistics over [NUM_ITERATIONS] iterations"
    iterations_line = lines[7].split()
    assert len(iterations_line) == 6
    num_iterations = int(iterations_line[4])

    assert is_thin_boundary(lines[8])

    # lines[9] == "mean median stddev" # (with padding for columns)
    assert lines[9].split() == ["mean", "median", "stddev"]

    assert is_thin_boundary(lines[10])

    # lines[11..18] == "[DATAPOINT NAME] [MEAN] ms [MEDIAN] ms [STDDEV] ms" # (with padding for columns)
    mt_presetup = parse_datapoint(lines[11])
    assert mt_presetup.datapoint_name == "MT Presetup"
    mt_setup = parse_datapoint(lines[12])
    assert mt_setup.datapoint_name == "MT Setup"
    sp_presetup = parse_datapoint(lines[13])
    assert sp_presetup.datapoint_name == "SP Presetup"
    sp_setup = parse_datapoint(lines[14])
    assert sp_setup.datapoint_name == "SP Setup"
    sb_presetup = parse_datapoint(lines[15])
    assert sb_presetup.datapoint_name == "SB Presetup"
    sb_setup = parse_datapoint(lines[16])
    assert sb_setup.datapoint_name == "SB Setup"
    base_ots = parse_datapoint(lines[17])
    assert base_ots.datapoint_name == "Base OTs"
    ot_extension_setup = parse_datapoint(lines[18])
    assert ot_extension_setup.datapoint_name == "OT Extension Setup"

    assert is_thin_boundary(lines[19])

    # lines[20..22] == "[DATAPOINT NAME] [MEAN] ms [MEDIAN] ms [STDDEV] ms" # (with padding for columns)
    preprocess_total = parse_datapoint(lines[20])
    assert preprocess_total.datapoint_name == "Preprocessing Total"
    gates_setup = parse_datapoint(lines[21])
    assert gates_setup.datapoint_name == "Gates Setup"
    gates_online = parse_datapoint(lines[22])
    assert gates_online.datapoint_name == "Gates Online"

    assert is_thin_boundary(lines[23])
    # lines[24] == "Circuit evaluation: [MEAN] ms [MEDIAN] ms [STDDEV] ms" # (with padding for columns)
    circuit_evaluation = parse_datapoint(lines[24])
    assert circuit_evaluation.datapoint_name == "Circuit Evaluation"

    assert is_thick_boundary(lines[25])

    assert lines[26] == "Communication with each other party:"
    communication = parse_communication_statistics(lines[27], lines[28])

    assert is_thick_boundary(lines[29])

    return TimingStatistics(
        num_iterations=num_iterations,
        mt_presetup=mt_presetup,
        mt_setup=mt_setup,
        sp_presetup=sp_presetup,
        sp_setup=sp_setup,
        sb_presetup=sb_presetup,
        sb_setup=sb_setup,
        base_ots=base_ots,
        ot_extension_setup=ot_extension_setup,
        preprocess_total=preprocess_total,
        gates_setup=gates_setup,
        gates_online=gates_online,
        circuit_evaluation=circuit_evaluation,
        communication=communication,
    )


@dataclass
class CircuitStatistics:
    num_gates: int
    num_inputs: int
    num_outputs: int
    num_simd_gates: int
    num_nonsimd_gates: int
    circuit_gen_time: float  # in milliseconds
    # depth: int

    @classmethod
    def from_dictionary(cls, params):
        num_gates = params['num_gates']
        num_inputs = params['num_inputs']
        num_outputs = params['num_outputs']
        num_simd_gates = params['num_simd_gates']
        num_nonsimd_gates = params['num_nonsimd_gates']
        circuit_gen_time = params['circuit_gen_time']
        # depth = params['depth']
        return cls(
            num_gates=num_gates,
            num_inputs=num_inputs,
            num_outputs=num_outputs,
            num_simd_gates=num_simd_gates,
            num_nonsimd_gates=num_nonsimd_gates,
            circuit_gen_time=circuit_gen_time,
            # depth = depth,
            )

    def to_dictionary(self):
        return {'num_gates': self.num_gates,
                'num_inputs': self.num_inputs,
                'num_outputs': self.num_outputs,
                'num_simd_gates': self.num_simd_gates,
                'num_nonsimd_gates': self.num_nonsimd_gates,
                'circuit_gen_time': self.circuit_gen_time,
                # 'depth': self.depth
                }

    @classmethod
    def by_accumulating_readings(cls, a, b):
        """
        These values should not change between runs

        NOTE: circuit generation time does change due to noise but it is not a 
        TimingDatapoint and I am too lazy to write code for it
        """
        return a


def parse_circuit_data(lines: list[str]) -> CircuitStatistics:
    gates_data = lines[0].split()
    assert gates_data[0] == "num_gates:"
    num_gates = int(gates_data[1])

    inputs_data = lines[1].split()
    assert inputs_data[0] == "num_inputs:"
    num_inputs = int(inputs_data[1])

    outputs_data = lines[2].split()
    assert outputs_data[0] == "num_outputs:"
    num_outputs = int(outputs_data[1])

    simd_gates_data = lines[3].split()
    assert simd_gates_data[0] == "num_simd_gates:"
    num_simd_gates = int(simd_gates_data[1])

    nonsimd_gates_data = lines[4].split()
    assert nonsimd_gates_data[0] == "num_nonsimd_gates:"
    num_nonsimd_gates = int(nonsimd_gates_data[1])

    # depth_data = lines[5].split()
    # assert depth_data[0] == "depth:"
    # depth = int(depth_data[1])

    circuit_gen_time_data = lines[5].split()
    assert circuit_gen_time_data[0] == "circuit_gen_time:"
    circuit_gen_time = float(circuit_gen_time_data[1])

    return CircuitStatistics(
        num_gates=num_gates,
        num_inputs=num_inputs,
        num_outputs=num_outputs,
        num_simd_gates=num_simd_gates,
        num_nonsimd_gates=num_nonsimd_gates,
        circuit_gen_time=circuit_gen_time,
        # depth=depth,
    )
