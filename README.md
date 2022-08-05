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

The script will look for `tests/config.yaml` in order to access the TrafficGen and the DUT. Other than the ssh access information, other information such as the interfaces connecting the DUT and the TrafficGen will also be provided in this file. A template `config_template.yaml` is provided as a sample. One can build a local config.yaml from this sample file.

```
dpdk_img: "docker.io/patrickkutch/dpdk:v21.11"
github_tests_path:          # URL to the test directory
                            # example: https://github.com/redhat-partner-solutions/intel-sriov-test/tree/main/sriov/tests
tests_doc_file: 	          # test specification name under the test case directory
                            # example: "README.md"
tests_name_field: 	        # name field in the test specification
                            # example: "Test Case Name:"
dut:
  host:                     # DUT ip address
  username: root            # need root access
  password:                 # root password
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

One may also choose to run the test script from the TrafficGen. In that case, the host will be `127.0.0.1`

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

In order for the html test report to be generated properly, the test case name line should start with "Test Case Name: ", or what is defined by `tests_name_field` in the config.yaml file. The script will try to match `tests_name_field` to locate the test case name.

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
