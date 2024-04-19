
from argparse import ArgumentParser
from main import logging
from dataclasses import dataclass

import socket

# from tests import context as test_context
# from tests.backends.motion.benchmark import run_benchmark as motion_run_benchmark
# from tests.backends.motion.benchmark import compile_benchmark as combine_compile_benchmark
# from tests.backends.motion.benchmark import run_benchmark_for_party as combine_run_benchmark_for_party
# from tests.backends.motion.benchmark import BenchmarkOutput as CombineBenchmarkOutput


# from utils import json_serialize, json_deserialize, StatsForInputConfig, StatsForTask, RunBenchmarkReq
from utils import GetAddressReq, GetAddressResp
from utils import read_message, write_message

log = logging.getLogger('combine.measure_costs')

@dataclass
class Party:
    index: int
    address: tuple[str, int]
    sock: socket

    @classmethod
    def from_dictionary(cls, params):
        index = params['index']
        address = params['address']

        return cls(
            index=index,
            address=address,
            sock=None
            )

    def to_dictionary(self):
        return {
            'index': self.index,
            'address': self.address,
        }


def run_party_0(address:str, port:int, n:int, timeout:int):
    log.info("starting party 0")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((address, int(port)))
    s.listen()
    parties:list[Party] = [Party(0, (address, port), None)]
    log.info("Party 0 listening for connections at address {} port {}".format(address, port))
    while True:
        conn, addr = s.accept()
        p = Party(index=len(parties), address=addr, sock=conn)
        parties.append(p)
        log.info("party {} from {} connected".format(p.index, p.address))
        conn.settimeout(timeout)
        if len(parties) == n:
            log.info("all parties are ready!")
            break

    # send a list of all parties to everyone
    for p in parties:
        if p.index == 0:
            continue
        parties_list_msg = [(p.index, p.address) for p in parties]
        write_message(p.sock, parties_list_msg)
    
    for p in parties:
        if p.index == 0:
            continue
        log.info("disconnected party {} at {}".format(p.index, p.address))
        p.sock.close()
    # while True:
    #     msg = read_message(conn)
    #     if not msg:
    #         log.error("Unable to read message from the client.")
    #         conn.close()
    #         break

    #     if isinstance(msg, GetAddressReq):
    #         log.info("Message is to get address")
    #         resp = GetAddressResp(addr)
    #         log.info("address is {}".format(addr))
    #         write_message(conn, resp)
    #     elif isinstance(msg, RunBenchmarkReq):
    #         log.info("Request to run: {} {} {}".format(msg.benchmark_name, msg.protocol, msg.vectorized))
    #         for dir in os.scandir(test_context.STAGES_DIR):
    #             if dir.name == msg.benchmark_name:
    #                 test_case_dir = dir
    #                 break
    #         log.info("path is {}".format(test_case_dir.path))
    #         resp = combine_run_benchmark_for_party(
    #                 MPC_PARTY_SERVER_ID, msg.party0_mpc_addr, msg.party1_mpc_addr, test_case_dir.name,
    #                 test_case_dir.path, msg.protocol, msg.vectorized, None, msg.cmd_args
    #             )
    #         write_message(conn, resp)

def run_party(address, port, i, n, timeout):
    log.info("starting party {}".format(i))
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((address, port))
    sock.settimeout(timeout)

    parties_list_msg = read_message(sock)
    for (p_index, p_address) in parties_list_msg:
        log.info("party {}: {}".format(p_index, p_address))

    # write_message(server_sock, GetAddressReq())
    # msg = read_message(server_sock)
    # my_ip = msg.client_address[0]
    # # my_ip = '127.0.0.1'
    # mpc_party_server = "0,{},23000".format(address)
    # mpc_party_client = "1,{},23001".format(my_ip)

if __name__ == "__main__":

    parser = ArgumentParser(
        description="measures costs of primitive operations e.g., +, *, <, etc for the supported backends")
    
    parser.add_argument('index',
        help="index of the party (0..n-1)", 
        type=int
    )
    
    parser.add_argument('-n', '--number',
        help="total number of parties (default=2)", 
        type=int,
        default=2
    )
    
    parser.add_argument('-a', '--address',
        help="address of the party with index 0. Party 0 acts as coordinator/server (default=127.0.0.1)", 
        default="127.0.0.1",
    )

    parser.add_argument('-p', '--port',
        help="port of the party with index 0. Party 0 acts as coordinator/server (default=42142)", 
        type=int,
        default=42142,
    )

    parser.add_argument('-t', '--timeout',
        help="connection timeout in seconds (default=3000)", 
        type=int,
        default=3000,
    )

    args = parser.parse_args()

    log.info("Running with address:{}, port: {}, index: {}, number: {},".format(args.address, args.port, args.index, args.number))

    if args.index == 0:
        run_party_0(args.address, args.port, args.number, args.timeout)
    else:
        run_party(args.address, args.port, args.index, args.number, args.timeout)

    # if args.graphs:
    #     generate_graphs(args.lan, args.wan)
    # elif args.compile:
    #     compile_all_benchmarks()
    # else:
    #     if args.role == 'b':
    #         run_paper_benchmarks()
    #     elif args.role == 's':
    #         run_server_role(args.address)
    #     else:
    #         run_client_role(args.address)
