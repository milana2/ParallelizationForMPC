from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, unique
from typing import Optional


@dataclass
class TimingDatapoint:
    datapoint_name: str

    mean: float
    median: float
    stddev: float
    # unit: str = 'ms'


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

    return CircuitStatistics(
        num_gates=num_gates,
        num_inputs=num_inputs,
        num_outputs=num_outputs,
        num_simd_gates=num_simd_gates,
        num_nonsimd_gates=num_nonsimd_gates,
    )
