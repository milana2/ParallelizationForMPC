# MPC Compiler

## [Generated results page](https://github.com/milana2/ParallelizationForMPC/blob/gh-pages/README.md)

## Setup instructions (Ubuntu)

1. Install Ubuntu dependencies
   ```sh
   sudo apt-get update
   sudo apt-get install graphviz python3 python3-pip
   ```

   MOTION dependencies:
   ```sh
   sudo apt-get install build-essential make git cmake libssl-dev libboost-program-options-dev
   ```

   MP-SPDZ dependencies:
   ```sh
   sudo apt-get install automake build-essential clang cmake git libboost-dev libboost-thread-dev libntl-dev libsodium-dev libssl-dev libtool m4 texinfo yasm
   ```
2. Clone the repo (the `--recursive` is required for the backend submodules)
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

## License

BSD 3-Clause License

Copyright (c) 2014-2023, [RPI-Purdue MPC team](AUTHORS.md)  
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

