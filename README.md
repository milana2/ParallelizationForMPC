# MPC Compiler

## [Generated results page](https://github.com/milana2/ParallelizationForMPC/blob/gh-pages/README.md)

## Setup instructions (Ubuntu)

1. Install Ubuntu dependencies with
   ```sh
   sudo apt-get update
   sudo apt-get install g++-10 make git python3 python3-pip cmake libssl-dev libboost-program-options-dev graphviz
   ```
2. Clone the repo (the `--recursive` is required for the MOTION submodule)
   ```sh
   git clone --recursive https://github.com/milana2/ParallelizationForMPC.git
   ```
3. Go to the `compiler` directory
   ```sh
   cd ParallelizationForMPC/compiler
   ```
4. Install Python dependencies
   ```sh
   pip install -r requirements.txt
   ```
   
## Run instructions

- `compiler/main.py` - Script for running the compiler and seeing text output for all the stages
- `compiler/run_tests.py` - Script for running the tests
- `compiler/make_results_markdown.py` - Script for generating the results page at https://github.com/milana2/ParallelizationForMPC/blob/gh-pages/README.md
