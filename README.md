# SR-IOV Tests for RHEL

## Test Connections

![alt text](/docs/images/SRIOV_RHEL_Test_Toplogy.jpg)


## Preconditions

A physical NIC card installed in the Device Under Test (DUT) capable of SR-IOV.  Includes BIOS settings enabling SR-IOV globally.

Two ports of the NIC under test are directly connected to the traffic generator (TrafficGen). In most of the test cases only one port is used. The second connection will be used for bonding tests.

## Required Packages

On the DUT server, the following RPM packages are required,
* tmux
* nmap

To install,
```
yum install -y tmux nmap
```

On the traffic generator server, the following RPM packages are required,
* nmap

To install,
```
yum install -y nmap
```

## Usage

The test script can be run from a third server. It will set up one ssh session to the TrafficGen and one to the DUT. The script will send commands over the ssh sessions to set up configuration or to send test traffic.

The test scripts supports both password-based and key-based ssh authentication. If the latter option is used, local user's ssh public key should be transferred to the DUT and trafficgen servers in advance.

The script will look for `tests/testbed.yaml` in order to access the TrafficGen and the DUT. Other than the ssh access information, other information such as the interfaces connecting the DUT and the TrafficGen will also be provided in this file. A template `testbed_template.yaml` is provided as a sample. One can build a local testbed.yaml from this sample file. The content of this file is explained below,

```
dut:
  host:                     # DUT ip address
  username: root            # need root access
  password:                 # root password (remove this line to use key-based ssh auth)
  pmd_cpus: "30,32,34"      # cpu list used for the testpmd
  interface:
    pf1:
      name: "ens7f3"        # first PF interface name
      pci: "0000:ca:00.3"   # first PF PCI address
    vf1:
      name: "ens7f3v0"      # first VF interface name
      pci: "0000:ca:19.0"   # first VF PCI address
trafficgen:
  host:                     # TrafficGen ip address
  username: root            # need root access
  password:                 # root password
  interface:
    pf1:
      name: "ens8f0"        # first PF interface name
      mac: "xx:xx:xx..."    # first PF mac address
```

If one chooses to run the test script from the TrafficGen, the trafficgen host will be `127.0.0.1`

Besides `tests/testbed.yaml`, the script will also look for `tests/config.yaml`. A template `config_template.yaml` is provided as a sample. In most situations, users can simply copy from this sample file into a local config.yaml. The content of this file is explained below,

```
dpdk_img: "docker.io/patrickkutch/dpdk:v21.11"  # DPDK build container image
github_tests_path:          # URL to the test directory
                            # example: https://github.com/redhat-partner-solutions/intel-sriov-test/tree/main/sriov/tests
tests_doc_file: 	          # test specification name under the test case directory
                            # example: "README.md"
tests_name_field: 	        # name field in the test specification
                            # example: "Test Case Name:"
```

Running the script from a python3 virtual environment is recommended. Install the required python modules,

```
python3 -m venv venv
source venv/bin/activate
pip install -r sriov/requirements.txt
```

To run a specific test case, say SR_IOV_Permutation,

```
cd sriov/tests/
pytest -v SR_IOV_Permutation
```

Certain test cases support multiple iterations. The number of iterations can be specified using the `--iteration` option. For example, to run the test case  `SR_IOV_MultipleVFCreation_withMTU` 10 times,
```
pytest -v --iteration=10 SR_IOV_MultipleVFCreation_withMTU
```

To run a specific test case and generate an HTML report file,
```
pytest -v --html=report.html --self-contained-html SR_IOV_Permutation
```

To run all SR-IOV test cases and generate an HTML report file,
```
pytest -v --html=report.html --self-contained-html SR*
```

After the test is completed, report.html will be generated under the current working directory.

## Test Case Description

Each test case has its own folder. Under this folder there are two files: `test_<testcase>.py` and `README.md`. The `README.md` under each test case folder contains the test case description. `test_<testcase>.py` is an reference implementation of this test case.

In order for the HTML test report to be generated properly, the test case name line should start with "Test Case Name: ", or what is defined by `tests_name_field` in the config.yaml file. The script will try to match `tests_name_field` to locate the test case name.

To satisfy the requirement of a unique identifier, the `README.md` of any SR-IOV test case must contain a distinct UUID. This will be used to formally reference a specific test specification. In order for the html test report to be generated properly, the UUID line should start with "UUID: ", or what is defined by the `tests_id_field` in the config.yaml file. Additionally, the reference implementation of a test should also be identified with a corresponding UUID, preferably as a comment on the first line. For example:
```
# UUID: defcb0a3-1d73-45f9-9438-f19c6fba8a8c
...
```
This will allow for clear identification of when a test specification and reference implementation may diverge. See `CONTRIBUTING.md` for more information on test case identification, and the generation of new UUIDs.

## Common Code

The common code shared by all test cases is under the `sriov/common`.

The common code has its own test cases. The majority of the common code test cases are under the `tests/common/` folder. Pytest is used to execute these test cases. Because a valid `config.yaml` file is expected by pytest to establish ssh connections and execute these test cases, they are considered an e2e test.

A small portion of common code test cases are done using mock. These mock unit test cases are under the `sriov/common` folder, along with the common code itself. The purpose of the mock unit tests is to cover scenarios that are difficult to cover via the e2e tests. These tests must be run from the root of the repo, unless one sets the `PYTHONPATH` environment variable to include the root, in which case the mock tests may be run from another directory.

## Debug Failed Test Case

When a test case is failing, one may want to immediately stop the test run and keep the failed setup for manual debugging. This can not be achieved with the pytest `-x` option, as `-x` still allow the cleanup to happen. Instead, this can be done by using the `--skipclean` option.

For example, if some permutation in `SR_IOV_Permutation_DPDK` has failed, re-run this test case like this,
```pytest -v --skipclean SR_IOV_Permutation_DPDK```

The test execution will stop immediately without cleaning up, and one may access the DUT and the trafficgen to debug.

After the debug is complete, one has to manually clean up the setup.
